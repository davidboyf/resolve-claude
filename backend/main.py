"""
FastAPI backend for Claude × DaVinci Resolve
"""
import os
import json
import asyncio
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

load_dotenv()

from claude_agent import stream_chat
import resolve_bridge as rb
from transcribe import transcribe, format_transcript_for_claude
from screen_capture import capture_screen, grab_resolve_frame, load_image_as_base64
from ai_generate import generate_image, add_image_to_timeline

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

app = FastAPI(title="Claude × DaVinci Resolve", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    messages: list
    model: str = "claude-sonnet-4-6"


class TranscribeRequest(BaseModel):
    video_path: str
    language: str = "en"
    model_size: str = "base"


class MarkerRequest(BaseModel):
    time_seconds: float
    color: str = "Blue"
    name: str = ""
    note: str = ""


class PlayheadRequest(BaseModel):
    time_seconds: float


class ColorWheelRequest(BaseModel):
    wheel: str
    red: float = 0.0
    green: float = 0.0
    blue: float = 0.0
    luma: float = 0.0
    track: int = 1
    clip_index: int = 0


class RenderRequest(BaseModel):
    preset_name: str
    output_path: str


# ─────────────────────────────────────────────
#  STATUS
# ─────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    return rb.get_status()


@app.get("/api/project")
async def get_project():
    try:
        return rb.get_project_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  CHAT (SSE streaming)
# ─────────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Stream Claude's response with DaVinci Resolve tool_use."""

    async def event_generator():
        try:
            async for event in stream_chat(
                messages=req.messages,
                model=req.model,
                api_key=ANTHROPIC_API_KEY,
            ):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)  # allow other tasks
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────────────────────
#  TIMELINE
# ─────────────────────────────────────────────

@app.get("/api/timeline")
async def get_timeline():
    try:
        return rb.get_timeline_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/timeline/markers")
async def get_markers():
    try:
        return rb.get_markers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/timeline/marker")
async def add_marker(req: MarkerRequest):
    try:
        return rb.add_marker(req.time_seconds, req.color, req.name, req.note)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/timeline/playhead")
async def set_playhead(req: PlayheadRequest):
    try:
        return rb.set_playhead(req.time_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/timeline/marker/delete")
async def delete_marker(req: PlayheadRequest):
    try:
        return rb.delete_marker(req.time_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/timeline/switch-page/{page}")
async def switch_page(page: str):
    try:
        return rb.switch_page(page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  MEDIA POOL
# ─────────────────────────────────────────────

@app.get("/api/media-pool")
async def get_media_pool():
    try:
        return rb.get_media_pool_clips()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  TRANSCRIBE
# ─────────────────────────────────────────────

@app.post("/api/transcribe")
async def transcribe_video(req: TranscribeRequest):
    """Transcribe a video file and return timestamped segments."""
    try:
        result = await asyncio.to_thread(
            transcribe,
            req.video_path,
            req.language,
            req.model_size,
        )
        result["formatted"] = format_transcript_for_claude(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  RENDER
# ─────────────────────────────────────────────

@app.get("/api/render/presets")
async def get_render_presets():
    try:
        return rb.get_render_presets()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/render/status")
async def get_render_status():
    try:
        return rb.get_render_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/render/start")
async def start_render(req: RenderRequest):
    try:
        return rb.start_render(req.preset_name, req.output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/render/cancel")
async def cancel_render():
    try:
        return rb.cancel_render()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  TIMELINES
# ─────────────────────────────────────────────

@app.get("/api/timelines")
async def list_timelines():
    try:
        return rb.list_timelines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/timelines/switch/{name}")
async def switch_timeline(name: str):
    try:
        return rb.switch_timeline(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  COLOR GRADE
# ─────────────────────────────────────────────

class ClipSelector(BaseModel):
    track: int = 1
    clip_index: int = 0


@app.post("/api/color/grade")
async def get_clip_grade(req: ClipSelector):
    try:
        return rb.get_clip_grade(req.track, req.clip_index)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  ENTRY
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  SCREEN CAPTURE
# ─────────────────────────────────────────────

@app.post("/api/resolve/screen")
async def capture_screen_endpoint():
    try:
        return await asyncio.to_thread(capture_screen)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resolve/frame")
async def capture_frame_endpoint():
    try:
        return await asyncio.to_thread(grab_resolve_frame)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  REFERENCE IMAGE
# ─────────────────────────────────────────────

class ReferenceImageRequest(BaseModel):
    path_or_url: str


@app.post("/api/reference-image/load")
async def load_reference_image(req: ReferenceImageRequest):
    try:
        return await asyncio.to_thread(load_image_as_base64, req.path_or_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  AI GENERATION
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    provider: str = "auto"
    width: int = 1920
    height: int = 1080
    style: str = "cinematic"


class DropToTimelineRequest(BaseModel):
    file_path: str
    position_seconds: float = -1
    duration_seconds: float = 3.0


@app.post("/api/ai/generate")
async def ai_generate(req: GenerateRequest):
    try:
        return await asyncio.to_thread(
            generate_image, req.prompt, req.provider, req.width, req.height, req.style
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/drop-to-timeline")
async def ai_drop_to_timeline(req: DropToTimelineRequest):
    try:
        return await asyncio.to_thread(
            add_image_to_timeline, req.file_path, req.position_seconds, req.duration_seconds
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
#  RENDER JOB DELETE
# ─────────────────────────────────────────────

@app.delete("/api/render/job/{job_id}")
async def delete_render_job(job_id: str):
    try:
        return rb.delete_render_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", 8765))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False, log_level="info")
