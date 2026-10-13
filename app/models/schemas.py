from pydantic import BaseModel
from typing import List, Optional


class ContentClassification(BaseModel):
    nsfw: bool
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
    frame_count: Optional[int] = None
    file_type: str = "image"
    raw_ai_response: Optional[str] = None
