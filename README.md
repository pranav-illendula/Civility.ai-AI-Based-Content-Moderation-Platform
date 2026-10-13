# ⚖ Civility AI — Content Moderation System
### Agentica 2.0 Hackathon · Team 34

AI-powered content moderation for images and videos.
Built with **FastAPI** + **Google Gemini 1.5 Flash Vision**.

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
> **Get a free key at:** https://aistudio.google.com/app/apikey

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
Upload an image or video for moderation.

**Request:** multipart/form-data
- `file`: JPG, PNG, WebP, MP4, or MOV (max 50 MB)

**Response:**
```json
{
  "general_description": "A group of people in a park...",
  "scene_elements": ["people", "trees", "outdoor"],
  "content_classification": {
    "nsfw": false,
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
  "file_type": "image"
}
```

---

## ⚙️ Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| GEMINI_API_KEY | — | Required. Google AI Studio key |
| MAX_FILE_SIZE_MB | 50 | Max upload size |
| FRAMES_PER_SECOND | 1 | Video sampling rate |

---

## 📁 Project Structure

```
civility_ai/
├── main.py
├── requirements.txt
├── .env.example
├── app/
│   ├── routes/analyze.py       # POST /api/analyze
│   ├── services/ai_analyzer.py # Gemini Vision
│   ├── utils/frame_extractor.py# OpenCV video frames
│   └── models/schemas.py       # Pydantic models
├── static/
│   ├── index.html
│   ├── style.css               # Agentica 2.0 branded
│   └── app.js
├── uploads/
└── frames/
```

## 🛠 Tech Stack
- Backend: FastAPI (Python)
- AI: Google Gemini 1.5 Flash Vision
- Video: OpenCV
- Frontend: Vanilla HTML/CSS/JS
- Brand: Bebas Neue + Montserrat fonts
