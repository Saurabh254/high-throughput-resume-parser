import asyncio
import base64
import json
import logging
import os
import time
from typing import Dict, Any, List
import redis.asyncio as redis
import httpx

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("ats-worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://localhost:8001")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_SERVICE_URL", "http://localhost:8002")

# Concurrency limits for batch processing
DEFAULT_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "16"))
PROGRESS_UPDATE_INTERVAL_SEC = 0.5


async def process_single_item(
    http_client: httpx.AsyncClient, 
    item: Dict[str, Any], 
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """
    Processes a single resume item with concurrency gating.
    Supports:
    - raw text: item['text']
    - base64 PDF: item['pdf_base64']
    - local file path: item['file_path']
    """
    async with semaphore:
        filename = item.get("filename", "batch_resume.pdf")
        
        try:
            # Case 1: Base64-encoded PDF
            if "pdf_base64" in item:
                pdf_bytes = base64.b64decode(item["pdf_base64"])
                files = {"file": (filename, pdf_bytes, "application/pdf")}
                data = {"auto_index": "true"}
                res = await http_client.post(
                    f"{INGESTION_URL}/api/v1/parse/pdf",
                    files=files,
                    data=data,
                    timeout=30.0
                )
                if res.status_code == 200:
                    return {"status": "success", "filename": filename, "data": res.json()}
                return {"status": "error", "filename": filename, "error": res.text}

            # Case 2: File path on shared volume
            elif "file_path" in item:
                path = item["file_path"]
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        pdf_bytes = f.read()
                    files = {"file": (os.path.basename(path), pdf_bytes, "application/pdf")}
                    res = await http_client.post(
                        f"{INGESTION_URL}/api/v1/parse/pdf",
                        files=files,
                        data={"auto_index": "true"},
                        timeout=30.0
                    )
                    if res.status_code == 200:
                        return {"status": "success", "filename": filename, "data": res.json()}
                    return {"status": "error", "filename": filename, "error": res.text}
                return {"status": "error", "filename": filename, "error": f"File path not found: {path}"}

            # Case 3: Raw text
            else:
                text_content = item.get("text", "")
                if not text_content:
                    return {"status": "error", "filename": filename, "error": "Empty text provided"}

                res = await http_client.post(
                    f"{INGESTION_URL}/api/v1/parse/text",
                    json={"text": text_content, "filename": filename, "auto_index": True},
                    timeout=30.0
                )
                if res.status_code == 200:
                    return {"status": "success", "filename": filename, "data": res.json()}
                return {"status": "error", "filename": filename, "error": res.text}

        except Exception as e:
            logger.error(f"Error processing item {filename}: {e}")
            return {"status": "error", "filename": filename, "error": str(e)}


async def process_batch_job(client: redis.Redis, job_data: dict):
    """
    Executes a high-throughput parallel batch ingestion job.
    Streams real-time progress via Redis Pub/Sub.
    """
    job_id = job_data.get("job_id", f"job_{int(time.time())}")
    items = job_data.get("items", [])
    total = len(items)
    concurrency = job_data.get("concurrency", DEFAULT_CONCURRENCY)

    logger.info(f"🚀 Starting batch job [{job_id}] with {total} items (concurrency: {concurrency})")

    start_time = time.time()
    semaphore = asyncio.Semaphore(concurrency)
    processed_count = 0
    success_count = 0
    failed_count = 0
    last_update_time = 0.0

    async def emit_progress(status: str = "processing"):
        nonlocal last_update_time
        now = time.time()
        elapsed = now - start_time
        throughput = round(processed_count / max(0.001, elapsed), 1)

        payload = {
            "job_id": job_id,
            "current": processed_count,
            "success": success_count,
            "failed": failed_count,
            "total": total,
            "percent": round((processed_count / max(1, total)) * 100, 1),
            "throughput_per_sec": throughput,
            "elapsed_seconds": round(elapsed, 2),
            "status": status,
        }
        await client.publish(f"ats:progress:{job_id}", json.dumps(payload))
        await client.setex(f"ats:job_state:{job_id}", 3600, json.dumps(payload))
        last_update_time = now

    # Emit initial status
    await emit_progress("started")

    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, timeout=60.0) as http_client:
        tasks = []
        for item in items:
            task = asyncio.create_task(process_single_item(http_client, item, semaphore))
            tasks.append(task)

        # Process results as they complete
        for future in asyncio.as_completed(tasks):
            result = await future
            processed_count += 1
            if result.get("status") == "success":
                success_count += 1
            else:
                failed_count += 1

            # Throttle progress reporting to avoid saturating Redis
            if time.time() - last_update_time >= PROGRESS_UPDATE_INTERVAL_SEC:
                await emit_progress("processing")

    # Final completion update
    await emit_progress("completed")
    total_elapsed = time.time() - start_time
    rate = processed_count / max(0.001, total_elapsed)
    logger.info(
        f"✅ Finished batch job [{job_id}]: {success_count} success, {failed_count} failed in {total_elapsed:.2f}s ({rate:.1f} items/s)"
    )


async def main():
    logger.info(f"Worker initializing. Connecting to Redis: {REDIS_URL}...")
    
    retry_delay = 2
    client: redis.Redis | None = None

    while True:
        try:
            # Set socket_timeout=15.0 so blocking blpop (timeout=2) never hits client TCP socket timeout
            client = redis.from_url(
                REDIS_URL, 
                decode_responses=True, 
                socket_timeout=15.0, 
                socket_connect_timeout=5.0
            )
            await client.ping()
            logger.info("Connected to Redis successfully.")
            logger.info(f"Worker listening for batch jobs on queue 'ats:batch:queue' (concurrency: {DEFAULT_CONCURRENCY})...")
            break
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(10, retry_delay * 2)

    while True:
        try:
            # BLPOP blocks for 2 seconds. When queue is idle, Redis returns None cleanly without socket timeout
            result = await client.blpop("ats:batch:queue", timeout=2)
            if result:
                queue_name, raw_data = result
                try:
                    job_data = json.loads(raw_data)
                    await process_batch_job(client, job_data)
                except json.JSONDecodeError as err:
                    logger.error(f"Malformed JSON in batch queue: {err}")
        except (redis.exceptions.TimeoutError, asyncio.TimeoutError):
            # Idle queue timeout tick - continue polling cleanly
            continue
        except asyncio.CancelledError:
            logger.info("Worker received cancel signal. Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"Worker event loop error: {e}")
            await asyncio.sleep(2)

    if client:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
