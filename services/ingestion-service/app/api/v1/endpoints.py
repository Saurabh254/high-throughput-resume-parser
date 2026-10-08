import io
import zipfile
import hashlib
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx

from app.core.config import settings
from app.core.pdf_extractor import PDFExtractor
from app.core.llm_parser import ExperienceDecompositionEngine, HeuristicExperienceParser
from app.cache.redis_cache import cache

try:
    from app.models.common import CandidateProfile
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../shared")))
    from models.common import CandidateProfile

logger = logging.getLogger(__name__)
router = APIRouter()

class TextParseRequest(BaseModel):
    text: str
    filename: Optional[str] = "manual_entry.txt"
    auto_index: bool = True

class BatchParseResponse(BaseModel):
    total_processed: int
    successful: int
    cached_hits: int
    failed: int
    profiles: List[CandidateProfile]

async def forward_to_orchestrator(profile: CandidateProfile):
    """Asynchronously forwards parsed candidate to Orchestrator Service to embed and store in pgvector."""
    try:
        url = f"{settings.ORCHESTRATOR_URL}/api/v1/index/candidate"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=profile.model_dump())
            if res.status_code in [200, 201]:
                logger.info(f"Successfully auto-indexed candidate: {profile.metadata.full_name} ({profile.file_hash[:8]})")
            else:
                logger.warning(f"Failed to auto-index candidate in orchestrator: {res.text}")
    except Exception as e:
        logger.warning(f"Orchestrator indexing service unreachable or failed: {e}")


@router.post("/parse/pdf", response_model=Dict[str, Any])
async def parse_single_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_index: bool = Form(True)
):
    """
    Parses a single PDF resume.
    1. Checks SHA-256 deduplication cache (0ms).
    2. Extracts clean text via PyMuPDF.
    3. Decomposes actual work experience via LLM / Deterministic NLP.
    4. Auto-indexes into pgvector in background.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_hash = hashlib.sha256(content).hexdigest()

    # Step 1: Check File Hash Cache
    cached_profile = await cache.get_by_file_hash(file_hash)
    if cached_profile:
        profile = CandidateProfile(**cached_profile)
        if auto_index:
            background_tasks.add_task(forward_to_orchestrator, profile)
        return {
            "cached": True,
            "file_hash": file_hash,
            "filename": file.filename,
            "profile": profile
        }

    # Step 2: In-memory PDF text extraction
    raw_text, meta = PDFExtractor.extract_from_bytes(content, filename=file.filename)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No readable text found in PDF (might be scanned image without OCR)")

    text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # Step 3: Check parsed text cache
    cached_text = await cache.get_by_text_hash(text_hash)
    if cached_text:
        cached_text["filename"] = file.filename
        cached_text["file_hash"] = file_hash
        profile = CandidateProfile(**cached_text)
        await cache.set_by_file_hash(file_hash, profile.model_dump())
        if auto_index:
            background_tasks.add_task(forward_to_orchestrator, profile)
        return {
            "cached": True,
            "file_hash": file_hash,
            "filename": file.filename,
            "profile": profile
        }

    # Step 4: Decompose actual work experiences and trajectory
    profile = await ExperienceDecompositionEngine.parse(raw_text, filename=file.filename, file_hash=file_hash)

    # Step 5: Save to multi-level caches
    profile_dict = profile.model_dump()
    await cache.set_by_file_hash(file_hash, profile_dict)
    await cache.set_by_text_hash(text_hash, profile_dict)

    # Step 6: Asynchronous vector indexing
    if auto_index:
        background_tasks.add_task(forward_to_orchestrator, profile)

    return {
        "cached": False,
        "file_hash": file_hash,
        "filename": file.filename,
        "profile": profile
    }


@router.post("/parse/text", response_model=Dict[str, Any])
async def parse_raw_text(
    payload: TextParseRequest,
    background_tasks: BackgroundTasks
):
    """
    Parses resume from raw text string.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    text_hash = hashlib.sha256(payload.text.encode("utf-8")).hexdigest()
    cached = await cache.get_by_text_hash(text_hash)
    if cached:
        profile = CandidateProfile(**cached)
        if payload.auto_index:
            background_tasks.add_task(forward_to_orchestrator, profile)
        return {"cached": True, "profile": profile}

    profile = await ExperienceDecompositionEngine.parse(
        payload.text, filename=payload.filename, file_hash=text_hash
    )
    await cache.set_by_text_hash(text_hash, profile.model_dump())

    if payload.auto_index:
        background_tasks.add_task(forward_to_orchestrator, profile)

    return {"cached": False, "profile": profile}


@router.post("/parse/batch", response_model=BatchParseResponse)
async def parse_batch_resumes(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    auto_index: bool = Form(True)
):
    """
    Processes multiple PDF files or a ZIP archive containing resumes.
    """
    profiles: List[CandidateProfile] = []
    cached_count = 0
    failed_count = 0

    all_pdf_items: List[tuple[str, bytes]] = []

    for f in files:
        content = await f.read()
        if f.filename.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for name in z.namelist():
                        if name.lower().endswith(".pdf") and not name.startswith("__MACOSX"):
                            all_pdf_items.append((name, z.read(name)))
            except Exception as e:
                logger.error(f"Error reading zip file {f.filename}: {e}")
                failed_count += 1
        elif f.filename.lower().endswith(".pdf"):
            all_pdf_items.append((f.filename, content))
        else:
            failed_count += 1

    for fname, pdf_bytes in all_pdf_items:
        try:
            f_hash = hashlib.sha256(pdf_bytes).hexdigest()
            cached_data = await cache.get_by_file_hash(f_hash)
            if cached_data:
                cached_count += 1
                prof = CandidateProfile(**cached_data)
                profiles.append(prof)
                if auto_index:
                    background_tasks.add_task(forward_to_orchestrator, prof)
                continue

            raw_text, _ = PDFExtractor.extract_from_bytes(pdf_bytes, filename=fname)
            if not raw_text.strip():
                failed_count += 1
                continue

            prof = await ExperienceDecompositionEngine.parse(raw_text, filename=fname, file_hash=f_hash)
            prof_dict = prof.model_dump()
            await cache.set_by_file_hash(f_hash, prof_dict)
            profiles.append(prof)

            if auto_index:
                background_tasks.add_task(forward_to_orchestrator, prof)
        except Exception as e:
            logger.error(f"Failed processing {fname}: {e}")
            failed_count += 1

    return BatchParseResponse(
        total_processed=len(all_pdf_items),
        successful=len(profiles),
        cached_hits=cached_count,
        failed=failed_count,
        profiles=profiles
    )
