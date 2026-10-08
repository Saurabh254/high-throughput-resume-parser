import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.worker import process_batch_job, process_single_item

@pytest.mark.asyncio
async def test_process_single_item_text():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"cached": False, "filename": "test.txt"}
    mock_client.post.return_value = mock_response

    semaphore = asyncio.Semaphore(4)
    item = {"text": "Alice Engineer at Stripe", "filename": "test.txt"}

    result = await process_single_item(mock_client, item, semaphore)
    assert result["status"] == "success"
    assert result["filename"] == "test.txt"

@pytest.mark.asyncio
async def test_process_batch_job():
    mock_redis = AsyncMock()
    
    with patch("httpx.AsyncClient") as mock_http_cls:
        mock_http = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "indexed"}
        mock_http.post.return_value = mock_response
        mock_http_cls.return_value.__aenter__.return_value = mock_http

        job_data = {
            "job_id": "test_job_123",
            "concurrency": 2,
            "items": [
                {"text": "Candidate 1", "filename": "c1.txt"},
                {"text": "Candidate 2", "filename": "c2.txt"}
            ]
        }

        await process_batch_job(mock_redis, job_data)

        # Check progress events were published to Redis
        assert mock_redis.publish.called
        assert mock_redis.setex.called
