# ⚖ Civility AI — Content Moderation System
### Agentica 2.0 Hackathon · Team 34

AI-powered content moderation for images, videos, and pasted text.
Built with **FastAPI**, local **PyTorch/Transformers** classifiers, and **Google Gemini** fallback.

---

## 🚀 Quick Start

### 1. Navigate into the project
```bash
cd civility_ai
```

### 2. Create your `.env` file
```bash
cp .env.example .env
```
Edit `.env` and paste your Gemini API key:
```
GEMINI_API_KEY=your_key_here
```
Place the supplied `vit_nsfw_model.pth` file in `models/`; the supplied class mapping is
stored there as `class_mapping.json`.
Override `IMAGE_MODEL_PATH` and `IMAGE_CLASS_MAPPING_PATH` in `.env` if you store them elsewhere.
The large checkpoint is intentionally excluded from Git.
Gemini is only required when a local classifier's confidence is between 40% and 65%.
The text classifiers download their model weights from Hugging Face on first use, then run inference locally.
> **Get a Gemini key at:** https://aistudio.google.com/app/apikey

### 3. Create virtual environment (recommended)
```bash
python -m venv venv
# Windows:   venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the server
```bash
uvicorn main:app --reload
```

### 6. Open browser
```
http://localhost:8000
```

---

## 🔌 API Reference

### POST /api/analyze
Upload an image or video for moderation. A local ViT model handles clear results;
Gemini Vision checks results with 40%-65% confidence.

**Request:** multipart/form-data
- `file`: JPG, PNG, WebP, MP4, or MOV (max 50 MB)

**Response:**
```json
{
  "general_description": "A group of people in a park...",
  "scene_elements": ["people", "trees", "outdoor"],
  "content_classification": {
    "nsfw": false,
    "vulgar": false,
    "violence": false,
    "bullying": false,
    "hate_speech": false,
    "illegal_content": false
  },
  "emotions_detected": ["happiness", "calm"],
  "severity_level": "none",
  "risk_reasoning": "The image shows a safe outdoor scene...",
  "final_verdict": "SAFE",
  "confidence_score": 0.97,
  "local_model_confidence": 0.97,
  "file_type": "image",
  "analysis_source": "local_vit"
}
```

### POST /api/analyze-text
Moderate a pasted sentence for NSFW content and vulgar/obscene language.

**Request:** JSON
```json
{
  "text": "Text to moderate"
}
```

Text is evaluated by local NSFW and obscenity Transformers classifiers first.
Gemini is called only when the combined local confidence is between 40% and 65%.
Text is limited to 5,000 characters.

---

## ⚙️ Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| GEMINI_API_KEY | — | Google AI Studio key, required only for uncertain results |
| MAX_FILE_SIZE_MB | 50 | Max upload size |
| FRAMES_PER_SECOND | 1 | Video sampling rate |
| IMAGE_MODEL_PATH | models/vit_nsfw_model.pth | Fine-tuned ViT checkpoint |
| IMAGE_CLASS_MAPPING_PATH | models/class_mapping.json | Labels for the ViT output classes |

---

## 📁 Project Structure

```
civility_ai/
├── main.py
├── requirements.txt
├── .env.example
├── app/
│   ├── routes/analyze.py       # POST /api/analyze
│   ├── services/ai_analyzer.py # Gemini Vision and text fallback
│   ├── services/image_classifier.py # Local ViT image/video classifier
│   ├── services/text_classifier.py  # Local NSFW and obscenity Transformers
│   ├── services/fallback_policy.py  # 40%-65% Gemini fallback band
│   ├── utils/frame_extractor.py# OpenCV video frames
│   └── models/schemas.py       # Pydantic models
├── models/
│   └── class_mapping.json      # NSFW/Neutral class IDs; checkpoint is local and git-ignored
├── static/
│   ├── index.html
│   ├── style.css               # Agentica 2.0 branded
│   └── app.js
├── uploads/
└── frames/
```

## 🛠 Tech Stack
- Backend: FastAPI (Python)
- Image/video: supplied fine-tuned ViT (PyTorch)
- Text: Hugging Face NSFW and obscenity classifiers (Transformers)
- Fallback: Google Gemini 2.5 Flash for uncertain local results
- Video: OpenCV
- Frontend: Vanilla HTML/CSS/JS
- Brand: Bebas Neue + Montserrat fonts
