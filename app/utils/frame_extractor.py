import cv2
import os
import uuid
import base64
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

FRAMES_DIR = Path("frames")
FRAMES_DIR.mkdir(exist_ok=True)


def extract_frames(video_path: str, fps: int = 1) -> List[str]:
    """Extract frames from a video at the given rate. Returns list of paths."""
    session_id = str(uuid.uuid4())[:8]
    session_dir = FRAMES_DIR / session_id
    session_dir.mkdir(exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_interval = max(1, int(video_fps / fps))
    frame_paths, idx, saved = [], 0, 0
    MAX_FRAMES = 30

    while cap.isOpened() and saved < MAX_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % frame_interval == 0:
            path = str(session_dir / f"frame_{saved:04d}.jpg")
            cv2.imwrite(path, frame)
            frame_paths.append(path)
            saved += 1
        idx += 1

    cap.release()
    logger.info(f"Extracted {len(frame_paths)} frames → {session_dir}")
    return frame_paths


def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def cleanup_frames(frame_paths: List[str]):
    for p in frame_paths:
        try:
            os.remove(p)
        except Exception:
            pass
    if frame_paths:
        try:
            Path(frame_paths[0]).parent.rmdir()
        except Exception:
            pass


def get_media_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {"jpeg": "image/jpeg", "jpg": "image/jpeg",
            "png": "image/png", "gif": "image/gif",
            "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")
