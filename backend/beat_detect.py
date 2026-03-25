"""
Beat detection using librosa.
Analyzes an audio/video file and returns beat timestamps.
"""
import os
import subprocess
import tempfile


def extract_audio_for_beats(file_path: str) -> str:
    """Extract mono 22050Hz audio from any video/audio file for librosa."""
    out = tempfile.mktemp(suffix=".wav")
    cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-ac", "1", "-ar", "22050", "-q:a", "0", "-map", "a",
        out
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"FFmpeg failed: {result.stderr.decode()}")
    return out


def detect_beats(file_path: str, bpm_hint: float = None) -> dict:
    """
    Detect beats in an audio or video file.
    Returns list of beat timestamps in seconds, estimated BPM, and downbeats.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        return {"error": "librosa not installed. Run: pip install librosa"}

    audio_path = None
    try:
        # Extract audio if it's a video file
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".mp4", ".mov", ".mxf", ".avi", ".mkv", ".r3d", ".braw"):
            audio_path = extract_audio_for_beats(file_path)
            load_path = audio_path
        else:
            load_path = file_path

        y, sr = librosa.load(load_path, sr=22050, mono=True)

        # Detect tempo and beats
        if bpm_hint:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, bpm=bpm_hint)
        else:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # Detect downbeats (every 4th beat typically)
        downbeat_times = beat_times[::4]

        # Onset detection for energy peaks (good cut points)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
        onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()

        # RMS energy — find high-energy moments
        rms = librosa.feature.rms(y=y)[0]
        rms_times = librosa.frames_to_time(range(len(rms)), sr=sr)
        top_energy_idx = np.argsort(rms)[-20:][::-1]
        energy_peaks = sorted([float(rms_times[i]) for i in top_energy_idx])

        bpm_val = float(tempo) if hasattr(tempo, '__float__') else float(tempo[0]) if len(tempo) > 0 else 120.0

        return {
            "success": True,
            "bpm": round(bpm_val, 1),
            "beat_count": len(beat_times),
            "beat_times": [round(t, 3) for t in beat_times],
            "downbeat_times": [round(t, 3) for t in downbeat_times],
            "onset_times": [round(t, 3) for t in onset_times[:50]],
            "energy_peaks": [round(t, 3) for t in energy_peaks],
            "duration": float(librosa.get_duration(y=y, sr=sr)),
            "file": file_path,
        }

    finally:
        if audio_path:
            try:
                os.unlink(audio_path)
            except Exception:
                pass


def beats_for_edit_style(beat_times: list, style: str = "every_beat") -> list:
    """
    Filter beat times based on edit style:
    - every_beat: cut on every beat
    - every_2: cut every 2 beats
    - every_4: cut every 4 beats (bars)
    - downbeats: cut only on downbeats (every 4th beat)
    - fast: every beat + onsets
    """
    if style == "every_beat":
        return beat_times
    elif style == "every_2":
        return beat_times[::2]
    elif style == "every_4" or style == "downbeats":
        return beat_times[::4]
    elif style == "every_8":
        return beat_times[::8]
    return beat_times
