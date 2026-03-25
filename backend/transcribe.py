"""
Audio extraction + Whisper transcription with timestamps.
"""
import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
    """Extract audio from a video file using FFmpeg. Returns path to .mp3 file."""
    if not output_path:
        tmp = tempfile.mktemp(suffix=".mp3")
        output_path = tmp

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-q:a", "0",
        "-map", "a",
        "-ac", "1",       # mono
        "-ar", "16000",   # 16kHz (optimal for Whisper)
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr}")
    return output_path


def transcribe(video_path: str, language: str = "en", model_size: str = "base") -> dict:
    """
    Transcribe a video file using OpenAI Whisper.
    Returns dict with full text and timestamped segments.
    """
    import whisper

    # Extract audio first
    audio_path = extract_audio(video_path)

    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            verbose=False,
        )

        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
                "words": [
                    {
                        "word": w["word"].strip(),
                        "start": round(w["start"], 2),
                        "end": round(w["end"], 2),
                    }
                    for w in seg.get("words", [])
                ],
            })

        return {
            "text": result["text"].strip(),
            "language": result.get("language", language),
            "segments": segments,
            "duration": segments[-1]["end"] if segments else 0,
        }
    finally:
        # Clean up temp audio file
        try:
            os.unlink(audio_path)
        except Exception:
            pass


def format_transcript_for_claude(transcript: dict) -> str:
    """Format a Whisper transcript into a clean text block for Claude."""
    lines = []
    for seg in transcript.get("segments", []):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]
        m_start = int(start // 60)
        s_start = start % 60
        lines.append(f"[{m_start:02d}:{s_start:05.2f}] {text}")
    return "\n".join(lines)
