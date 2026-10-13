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

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
# Windows:   venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download the image model
The fine-tuned ViT checkpoint (about 328 MB) is too large for GitHub, so it is hosted on Hugging Face:
**https://huggingface.co/pranav200621/vit-nsfw-classifier**

Download it into the `models/` folder with the Hugging Face CLI:
```bash
pip install -U huggingface_hub
hf download pranav200621/vit-nsfw-classifier --local-dir models
```

Or download the files manually and place them in `models/`:

| File | Direct link |
|------|-------------|
| `vit_nsfw_model.pth` | https://huggingface.co/pranav200621/vit-nsfw-classifier/resolve/main/vit_nsfw_model.pth |
| `class_mapping.json` | https://huggingface.co/pranav200621/vit-nsfw-classifier/resolve/main/class_mapping.json |

After downloading, your folder should look like this:
```
models/
├── vit_nsfw_model.pth
└── class_mapping.json
```

> **Note:** `class_mapping.json` is also tracked in this repo. The `.pth` checkpoint is git-ignored.

### 5. Create your `.env` file
```bash
cp .env.example .env
```
Edit `.env` and paste your Gemini API key:
```
GEMINI_API_KEY=your_key_here
```
- Override `IMAGE_MODEL_PATH` and `IMAGE_CLASS_MAPPING_PATH` in `.env` if you store the model files elsewhere.
- Gemini is only required when a local classifier's confidence is between 40% and 65%.
- The text classifiers download their model weights from Hugging Face on first use, then run inference locally.

> **Get a Gemini key at:** https://aistudio.google.com/app/apikey

### 6. Run the server
```bash
uvicorn main:app --reload
```

### 7. Open browser
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

## 🧯 Troubleshooting

| Problem | Fix |
|---------|-----|
| Error about a missing model file at startup | Complete **step 4** and confirm `models/vit_nsfw_model.pth` exists |
| `hf: command not found` | Download the files manually from the links in step 4, or reopen your terminal after installing `huggingface_hub` |
| Text classifier is slow on the first request | The Hugging Face text models download on first use, so later requests are faster |
| Gemini errors on uncertain results | Check that `GEMINI_API_KEY` is set correctly in `.env` |

---

## 📁 Project Structure

```
civility_ai/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── app/
│   ├── routes/analyze.py            # POST /api/analyze
│   ├── services/ai_analyzer.py      # Gemini Vision and text fallback
│   ├── services/image_classifier.py # Local ViT image/video classifier
│   ├── services/text_classifier.py  # Local NSFW and obscenity Transformers
│   ├── services/fallback_policy.py  # 40%-65% Gemini fallback band
│   ├── utils/frame_extractor.py     # OpenCV video frames
│   └── models/schemas.py            # Pydantic models
├── models/
│   └── class_mapping.json           # NSFW/Neutral class IDs; the .pth checkpoint is downloaded from Hugging Face and git-ignored
├── static/
│   ├── index.html
│   ├── style.css                    # Agentica 2.0 branded
│   └── app.js
├── uploads/
└── frames/
```

## 🛠 Tech Stack
- Backend: FastAPI (Python)
- Image/video: fine-tuned ViT (PyTorch), hosted on [Hugging Face](https://huggingface.co/pranav200621/vit-nsfw-classifier)
- Text: Hugging Face NSFW and obscenity classifiers (Transformers)
- Fallback: Google Gemini 2.5 Flash for uncertain local results
- Video: OpenCV
- Frontend: Vanilla HTML/CSS/JS
- Brand: Bebas Neue + Montserrat fonts