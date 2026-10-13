import os
import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from starlette.concurrency import run_in_threadpool

from app.services.ai_analyzer import analyze_text_with_ai, analyze_with_ai
from app.services.fallback_policy import needs_gemini_fallback
from app.services.image_classifier import classify_images
from app.services.text_classifier import classify_text
from app.utils.frame_extractor import extract_frames, cleanup_frames
from app.models.schemas import (
    AnalysisResult,
    ContentClassification,
    TextAnalysisRequest,
)

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
    safe_filename = Path(file.filename or "upload").name
    saved_path = UPLOADS_DIR / f"{session_id}_{safe_filename}"
    frames = []

    try:
        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_BYTES:
            raise HTTPException(413, f"File exceeds {MAX_BYTES // 1024 // 1024} MB limit.")

        saved_path.write_bytes(raw_bytes)
        logger.info(f"Saved: {saved_path} ({len(raw_bytes)/1024:.1f} KB)")

        if is_image:
            image_paths = [str(saved_path)]

        else:  # video
            fps = int(os.getenv("FRAMES_PER_SECOND", 1))
            try:
                frames = extract_frames(str(saved_path), fps=fps)
            except ValueError as e:
                raise HTTPException(422, str(e))
            if not frames:
                raise HTTPException(422, "Could not extract frames from video.")
            image_paths = frames

        prediction = await run_in_threadpool(classify_images, image_paths)
        frame_count = len(frames) if is_video else None
        file_type = "video" if is_video else "image"

        if needs_gemini_fallback(prediction.confidence):
            result = await analyze_with_ai(image_paths, file_type=file_type)
            result.local_model_confidence = prediction.confidence
        else:
            is_nsfw = prediction.is_nsfw
            result = AnalysisResult(
                general_description=(
                    "The trained ViT classifier detected NSFW content."
                    if is_nsfw
                    else "The trained ViT classifier detected no NSFW content."
                ),
                scene_elements=[],
                content_classification=ContentClassification(
                    nsfw=is_nsfw,
                    vulgar=False,
                    violence=False,
                    bullying=False,
                    hate_speech=False,
                    illegal_content=False,
                ),
                emotions_detected=[],
                severity_level="high" if is_nsfw else "none",
                risk_reasoning=(
                    f"Local ViT classification confidence: {prediction.confidence:.1%}."
                ),
                final_verdict="FLAGGED" if is_nsfw else "SAFE",
                confidence_score=prediction.confidence,
                local_model_confidence=prediction.confidence,
                frame_count=frame_count,
                file_type=file_type,
                analysis_source="local_vit",
            )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        logger.exception(e)
        raise HTTPException(500, f"Analysis failed: {e}")
    finally:
        cleanup_frames(frames)
        try:
            saved_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/analyze-text", response_model=AnalysisResult)
async def analyze_text(request: TextAnalysisRequest):
    """POST /api/analyze-text — moderate a sentence locally with Gemini fallback."""
    text = request.text.strip()
    if not text:
        raise HTTPException(400, "Text to analyze cannot be empty.")
    if len(text) > 5000:
        raise HTTPException(413, "Text exceeds the 5000 character limit.")

    try:
        prediction = await run_in_threadpool(classify_text, text)
    except ValueError as e:
        raise HTTPException(500, str(e))

    if needs_gemini_fallback(prediction.confidence):
        try:
            result = await analyze_text_with_ai(text)
            result.local_model_confidence = prediction.confidence
            return result
        except ValueError as e:
            raise HTTPException(500, str(e))

    is_nsfw = prediction.nsfw_probability >= 0.5
    is_vulgar = prediction.vulgar_probability >= 0.5
    is_risky = is_nsfw or is_vulgar
    risk_labels = []
    if is_nsfw:
        risk_labels.append("NSFW")
    if is_vulgar:
        risk_labels.append("vulgar language")
    reasoning = (
        f"Local Transformers classification confidence: {prediction.confidence:.1%}."
    )
    if risk_labels:
        reasoning += f" Detected: {', '.join(risk_labels)}."

    return AnalysisResult(
        general_description="Pasted text was analyzed by local Transformers classifiers.",
        scene_elements=[],
        content_classification=ContentClassification(
            nsfw=is_nsfw,
            vulgar=is_vulgar,
            violence=False,
            bullying=False,
            hate_speech=False,
            illegal_content=False,
        ),
        emotions_detected=[],
        severity_level="high" if is_nsfw else "medium" if is_vulgar else "none",
        risk_reasoning=reasoning,
        final_verdict="FLAGGED" if is_risky else "SAFE",
        confidence_score=prediction.confidence,
        local_model_confidence=prediction.confidence,
        file_type="text",
        analysis_source="local_transformers",
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "Civility AI", "version": "1.0.0"}
