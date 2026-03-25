# Claude × DaVinci Resolve

A local AI editing assistant that gives Claude full control over your open DaVinci Resolve project. Chat naturally to cut clips, color grade, balance audio, add markers, run Fusion VFX, and render — all without touching the Resolve UI.

![Claude × DaVinci Resolve](https://img.shields.io/badge/DaVinci%20Resolve-Studio-blue?style=flat-square) ![Claude](https://img.shields.io/badge/Claude-Sonnet%204.6-purple?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.10+-green?style=flat-square)

## What Claude can do

| Category | Actions |
|---|---|
| **Timeline** | Read all clips, tracks, durations; split clips; delete ranges; move playhead |
| **Markers** | Add colored markers with labels/notes; delete markers |
| **Color Grading** | Adjust Lift/Gamma/Gain/Offset wheels; contrast & saturation; apply LUTs; add serial nodes; reset grades |
| **Audio** | Set track volumes (dB); mute/unmute tracks; set individual clip volumes |
| **Navigation** | Switch between Edit, Color, Fusion, Fairlight, Deliver pages |
| **Media Pool** | List all clips with paths, resolution, duration |
| **Render** | List presets; start render jobs |
| **Fusion** | Open Fusion page for any clip |
| **Transcription** | Transcribe any video file via Whisper (with word-level timestamps) |

## Architecture

```
Browser (React UI)
      ↕ HTTP/SSE
FastAPI (Python) :8765
   ├── Claude API (Anthropic) — streaming tool_use
   └── DaVinci Resolve Python API — live project control
```

## Requirements

- **DaVinci Resolve Studio** (paid version — free version has scripting disabled)
- Python 3.10+
- Node.js 18+
- FFmpeg (for transcription): `brew install ffmpeg`
- An [Anthropic API key](https://console.anthropic.com/)

## Setup

### 1. Enable scripting in DaVinci Resolve

Open DaVinci Resolve → **Preferences → General → External Scripting Using** → set to **"Local"**

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

python main.py
# Backend runs on http://127.0.0.1:8765
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Opens on http://localhost:5173
```

### 4. Open in browser

Navigate to **http://localhost:5173** — Claude is now connected to your open Resolve project.

## Usage examples

Just type naturally:

- *"Analyze my timeline and tell me what's on it"*
- *"Add blue markers labeled 'Good take' at every clip that's longer than 10 seconds"*
- *"Apply a warm cinematic look to clip 1: lift the shadows slightly blue, add orange to the highlights, contrast 1.15"*
- *"Cut all clips between 0:30 and 1:45 on track 1"*
- *"Set audio track 2 to -12dB and mute track 3"*
- *"Switch to the Color page and add a new serial node labeled 'Skin Tone Fix'"*
- *"Start a render using the H.264 Master preset to my Desktop"*

## Model recommendations

| Model | Best for |
|---|---|
| **Sonnet 4.6** (default) | All real-time chat and editing |
| **Opus 4.6** | Deep analysis, complex multi-step edits |
| **Haiku 4.5** | Simple single actions (fastest/cheapest) |

## Transcription (optional)

To use the "analyze and transcribe" feature, FFmpeg and Whisper must be installed:

```bash
pip install openai-whisper
brew install ffmpeg  # macOS
```

Then tell Claude: *"Transcribe the file at /path/to/video.mp4 and cut out any sections where nobody is speaking"*

## Troubleshooting

**"Cannot import DaVinciResolveScript"**
→ Make sure DaVinci Resolve is open and External Scripting is set to "Local" in Preferences → General

**"No project open"**
→ Open a project in Resolve before starting the backend

**Backend won't start**
→ Check your `.env` has a valid `ANTHROPIC_API_KEY`

## License

MIT
