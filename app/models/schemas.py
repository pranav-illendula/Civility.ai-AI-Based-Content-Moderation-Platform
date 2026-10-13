from pydantic import BaseModel
from typing import List, Optional


class ContentClassification(BaseModel):
    nsfw: bool
    vulgar: bool = False
    violence: bool
    bullying: bool
    hate_speech: bool
    illegal_content: bool


class AnalysisResult(BaseModel):
    general_description: str
    scene_elements: List[str]
    content_classification: ContentClassification
    emotions_detected: List[str]
    severity_level: str        # none | low | medium | high | critical
    risk_reasoning: str
    final_verdict: str         # SAFE | REVIEW NEEDED | FLAGGED | BLOCKED
    confidence_score: Optional[float] = None
    local_model_confidence: Optional[float] = None
    frame_count: Optional[int] = None
    file_type: str = "image"
    analysis_source: str = "gemini"
    raw_ai_response: Optional[str] = None


class TextAnalysisRequest(BaseModel):
    text: str
