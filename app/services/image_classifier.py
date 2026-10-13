import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

MODEL_IMAGE_SIZE = 224
_model = None
_device = None
_nsfw_class_id = None
_model_lock = threading.Lock()


@dataclass
class ImagePrediction:
    nsfw_probability: float
    confidence: float

    @property
    def is_nsfw(self) -> bool:
        return self.nsfw_probability >= 0.5


def _load_model():
    global _model, _device, _nsfw_class_id

    if _model is not None:
        return _model, _device, _nsfw_class_id

    with _model_lock:
        if _model is not None:
            return _model, _device, _nsfw_class_id

        import torch
        from transformers import ViTConfig, ViTForImageClassification

        model_path = Path(os.getenv("IMAGE_MODEL_PATH", "models/vit_nsfw_model.pth"))
        mapping_path = Path(os.getenv("IMAGE_CLASS_MAPPING_PATH", "models/class_mapping.json"))
        if not model_path.is_file():
            raise FileNotFoundError(f"Image model checkpoint not found: {model_path}")
        if not mapping_path.is_file():
            raise FileNotFoundError(f"Image class mapping not found: {mapping_path}")

        with mapping_path.open("r", encoding="utf-8") as mapping_file:
            class_mapping = json.load(mapping_file)
        normalized_mapping = {str(label).strip().casefold(): int(class_id)
                              for label, class_id in class_mapping.items()}
        if set(normalized_mapping) != {"nsfw", "neutral"}:
            raise ValueError("Image class mapping must contain NSFW and Neutral labels.")
        if sorted(normalized_mapping.values()) != list(range(len(normalized_mapping))):
            raise ValueError("Image class mapping IDs must be contiguous and start at zero.")

        config = ViTConfig(
            image_size=MODEL_IMAGE_SIZE,
            patch_size=16,
            hidden_size=768,
            num_hidden_layers=12,
            num_attention_heads=12,
            intermediate_size=3072,
            num_labels=len(normalized_mapping),
            id2label={class_id: label for label, class_id in normalized_mapping.items()},
            label2id={label: class_id for label, class_id in normalized_mapping.items()},
        )
        model = ViTForImageClassification(config)
        checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
        if isinstance(checkpoint, dict):
            checkpoint = checkpoint.get(
                "state_dict", checkpoint.get("model_state_dict", checkpoint)
            )
        if not isinstance(checkpoint, dict):
            raise ValueError("Image checkpoint must contain a model state dictionary.")
        if checkpoint and all(key.startswith("module.") for key in checkpoint):
            checkpoint = {key.removeprefix("module."): value
                          for key, value in checkpoint.items()}
        model.load_state_dict(checkpoint, strict=True)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        _model = model
        _device = device
        _nsfw_class_id = normalized_mapping["nsfw"]
        logger.info("Loaded local ViT moderation model on %s", device)
        return _model, _device, _nsfw_class_id


def _image_tensor(image_path: str, torch):
    with Image.open(image_path) as image:
        image = image.convert("RGB").resize(
            (MODEL_IMAGE_SIZE, MODEL_IMAGE_SIZE), Image.Resampling.BILINEAR
        )
        pixels = np.asarray(image, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(pixels).permute(2, 0, 1)
    return ((tensor - 0.5) / 0.5).unsqueeze(0)


def classify_images(image_paths: List[str]) -> ImagePrediction:
    """Classify an image or video frames using the supplied fine-tuned ViT."""
    if not image_paths:
        raise ValueError("At least one image is required for classification.")

    import torch

    model, device, nsfw_class_id = _load_model()
    frame_probabilities = []
    with torch.inference_mode():
        for image_path in image_paths:
            inputs = _image_tensor(image_path, torch).to(device)
            logits = model(pixel_values=inputs).logits
            probability = torch.softmax(logits, dim=-1)[0, nsfw_class_id].item()
            frame_probabilities.append(float(probability))

    # A single NSFW frame is sufficient to flag a video.
    nsfw_probability = max(frame_probabilities)
    confidence = max(nsfw_probability, 1.0 - nsfw_probability)
    return ImagePrediction(nsfw_probability=nsfw_probability, confidence=confidence)
