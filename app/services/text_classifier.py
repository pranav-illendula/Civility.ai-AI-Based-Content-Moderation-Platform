import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NSFW_TEXT_MODEL = "michellejieli/NSFW_text_classifier"
VULGAR_TEXT_MODEL = "unitary/toxic-bert"

_models = None
_device = None
_model_lock = threading.Lock()


@dataclass
class TextPrediction:
    nsfw_probability: float
    vulgar_probability: float

    @property
    def risk_probability(self) -> float:
        return max(self.nsfw_probability, self.vulgar_probability)

    @property
    def confidence(self) -> float:
        return max(self.risk_probability, 1.0 - self.risk_probability)


def _load_models():
    global _models, _device

    if _models is not None:
        return _models, _device

    with _model_lock:
        if _models is not None:
            return _models, _device

        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        nsfw_tokenizer = AutoTokenizer.from_pretrained(NSFW_TEXT_MODEL)
        nsfw_model = AutoModelForSequenceClassification.from_pretrained(NSFW_TEXT_MODEL)
        vulgar_tokenizer = AutoTokenizer.from_pretrained(VULGAR_TEXT_MODEL)
        vulgar_model = AutoModelForSequenceClassification.from_pretrained(VULGAR_TEXT_MODEL)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        nsfw_model.to(device).eval()
        vulgar_model.to(device).eval()
        _models = (nsfw_tokenizer, nsfw_model, vulgar_tokenizer, vulgar_model)
        _device = device
        logger.info("Loaded local NSFW and obscenity text classifiers on %s", device)
        return _models, _device


def _label_id(model, label: str) -> int:
    for class_id, class_name in model.config.id2label.items():
        if str(class_name).casefold() == label.casefold():
            return int(class_id)
    raise ValueError(f"Text classifier does not contain the expected '{label}' label.")


def classify_text(text: str) -> TextPrediction:
    """Score sexual NSFW content and obscene/vulgar language locally."""
    if not text.strip():
        raise ValueError("Text to analyze cannot be empty.")

    import torch

    (nsfw_tokenizer, nsfw_model, vulgar_tokenizer, vulgar_model), device = _load_models()
    nsfw_id = _label_id(nsfw_model, "NSFW")
    obscene_id = _label_id(vulgar_model, "obscene")

    nsfw_inputs = nsfw_tokenizer(
        text, return_tensors="pt", truncation=True, max_length=512
    ).to(device)
    vulgar_inputs = vulgar_tokenizer(
        text, return_tensors="pt", truncation=True, max_length=512
    ).to(device)

    with torch.inference_mode():
        nsfw_probabilities = torch.softmax(
            nsfw_model(**nsfw_inputs).logits, dim=-1
        )[0]
        vulgar_probabilities = torch.sigmoid(
            vulgar_model(**vulgar_inputs).logits
        )[0]

    return TextPrediction(
        nsfw_probability=float(nsfw_probabilities[nsfw_id].item()),
        vulgar_probability=float(vulgar_probabilities[obscene_id].item()),
    )
