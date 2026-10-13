import os
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.ai_analyzer import analyze_with_ai
from app.utils.frame_extractor import extract_frames, cleanup_frames
from app.models.schemas import AnalysisResult

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

ALLOWED_IMAGE = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_VIDEO = {"video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo"}
MAX_BYTES = int(os.getenv("MAX_FILE_SIZE_MB", 50)) * 1024 * 1024


def _infer_content_type(filename: str, ct: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    mapping = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "mp4": "video/mp4", "mov": "video/quicktime",
    }
    return mapping.get(ext, ct or "")


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_content(file: UploadFile = File(...)):
    """POST /api/analyze — analyze an image or video for harmful content."""
    ct = _infer_content_type(file.filename or "", file.content_type or "")
    is_image = ct in ALLOWED_IMAGE
    is_video = ct in ALLOWED_VIDEO

    if not is_image and not is_video:
        raise HTTPException(400, f"Unsupported file type '{ct}'. Allowed: jpg, png, webp, mp4, mov.")

    session_id = str(uuid.uuid4())[:8]
    saved_path = UPLOADS_DIR / f"{session_id}_{file.filename}"

    try:
        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_BYTES:
            raise HTTPException(413, f"File exceeds {MAX_BYTES // 1024 // 1024} MB limit.")

        saved_path.write_bytes(raw_bytes)
        logger.info(f"Saved: {saved_path} ({len(raw_bytes)/1024:.1f} KB)")

        if is_image:
            result = await analyze_with_ai([str(saved_path)], file_type="image")

        else:  # video
            fps = int(os.getenv("FRAMES_PER_SECOND", 1))
            frames = extract_frames(str(saved_path), fps=fps)
            if not frames:
                raise HTTPException(422, "Could not extract frames from video.")
            result = await analyze_with_ai(frames, file_type="video")
            cleanup_frames(frames)

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception(e)
        raise HTTPException(500, f"Analysis failed: {e}")
    finally:
        try:
            saved_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Civility AI", "version": "1.0.0"}
