import os
import json
import re
import logging
import base64
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from app.models.schemas import AnalysisResult, ContentClassification

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-1.5-flash"   # supports vision + is free-tier friendly

SYSTEM_PROMPT = """You are Civility AI, a professional content moderation system built for the Agentica 2.0 Hackathon.
Analyze the provided image(s) and return ONLY a valid JSON object. No markdown fences, no explanation — raw JSON only.

Required JSON structure:
{
  "general_description": "Concise description of the content",
  "scene_elements": ["element1", "element2"],
  "content_classification": {
    "nsfw": true,
    "violence": false,
    "bullying": false,
    "hate_speech": false,
    "illegal_content": false
  },
  "emotions_detected": ["emotion1", "emotion2"],
  "severity_level": "none | low | medium | high | critical",
  "risk_reasoning": "Clear explanation of why content is or is not risky",
  "final_verdict": "SAFE | REVIEW NEEDED | FLAGGED | BLOCKED",
  "confidence_score": 0.95
}

Be objective, accurate, and professional. Err on the side of caution for ambiguous content."""


def _parse(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    text = re.sub(r"\s*```$", "", text).strip()
    # Handle cases where model wraps in extra whitespace
    text = text.strip()
    return json.loads(text)


def _build(data: dict, file_type: str, frame_count: Optional[int], raw: str) -> AnalysisResult:
    cc = data.get("content_classification", {})
    return AnalysisResult(
        general_description=data.get("general_description", "No description available."),
        scene_elements=data.get("scene_elements", []),
        content_classification=ContentClassification(
            nsfw=bool(cc.get("nsfw", False)),
            violence=bool(cc.get("violence", False)),
            bullying=bool(cc.get("bullying", False)),
            hate_speech=bool(cc.get("hate_speech", False)),
            illegal_content=bool(cc.get("illegal_content", False)),
        ),
        emotions_detected=data.get("emotions_detected", []),
        severity_level=data.get("severity_level", "none"),
        risk_reasoning=data.get("risk_reasoning", ""),
        final_verdict=data.get("final_verdict", "REVIEW NEEDED"),
        confidence_score=float(data.get("confidence_score", 0.85)),
        frame_count=frame_count,
        file_type=file_type,
        raw_ai_response=raw,
    )


def _read_image_part(image_path: str) -> dict:
    """Build a Gemini inline_data image part from a file path."""
    ext = Path(image_path).suffix.lower().lstrip(".")
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
    mime = mime_map.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        b64data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {"inline_data": {"mime_type": mime, "data": b64data}}


async def analyze_with_ai(image_paths: List[str], file_type: str = "image") -> AnalysisResult:
    """Analyze images/frames using Google Gemini Vision."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env file.")

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
    )

    # Build parts list: optional text intro + images + final instruction
    parts = []

    if file_type == "video":
        parts.append(
            f"These are {len(image_paths)} frames sampled from a video at 1 frame/second. "
            "Analyze the overall content across all frames holistically."
        )

    for path in image_paths:
        parts.append(_read_image_part(path))

    parts.append("Analyze this content and return ONLY the JSON moderation report.")

    logger.info(f"Sending {len(image_paths)} image(s) to Gemini ({file_type})")

    response = model.generate_content(parts)
    raw = response.text
    logger.info(f"Gemini response preview: {raw[:200]}")

    data = _parse(raw)
    return _build(data, file_type, len(image_paths) if file_type == "video" else None, raw)
