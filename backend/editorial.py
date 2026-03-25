"""
Editorial intelligence — audio analysis, clip scoring, smart assembly.
Gives Claude real data to make editorial decisions like a human editor.
"""
import os
import re
import json
import subprocess
import tempfile
from typing import Optional


# ─────────────────────────────────────────────
#  AUDIO ANALYSIS
# ─────────────────────────────────────────────

def get_audio_energy(file_path: str) -> dict:
    """
    Use FFmpeg to get mean/max volume and duration of an audio or video file.
    Returns loudness data Claude can use to find the best moments.
    """
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", "volumedetect",
        "-vn", "-sn", "-dn",
        "-f", "null", "/dev/null"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    output = result.stderr

    mean_vol = None
    max_vol = None
    duration = None

    for line in output.splitlines():
        if "mean_volume" in line:
            m = re.search(r"mean_volume:\s*([-\d.]+)", line)
            if m:
                mean_vol = float(m.group(1))
        if "max_volume" in line:
            m = re.search(r"max_volume:\s*([-\d.]+)", line)
            if m:
                max_vol = float(m.group(1))
        if "Duration" in line:
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
            if m:
                h, mi, s = m.groups()
                duration = int(h)*3600 + int(mi)*60 + float(s)

    return {
        "file": file_path,
        "mean_volume_db": mean_vol,
        "max_volume_db": max_vol,
        "duration_seconds": duration,
        "has_audio": mean_vol is not None,
        "energy_level": _classify_energy(mean_vol),
    }


def _classify_energy(db: Optional[float]) -> str:
    if db is None:
        return "unknown"
    if db > -15:
        return "high"
    if db > -25:
        return "medium"
    if db > -40:
        return "low"
    return "silent"


def get_waveform_peaks(file_path: str, num_segments: int = 20) -> dict:
    """
    Divide the audio into segments and get RMS energy per segment.
    Returns a list of (time, energy) tuples — lets Claude find the most energetic moments.
    """
    # Get duration first
    info = get_audio_energy(file_path)
    duration = info.get("duration_seconds", 0)
    if not duration:
        return {"error": "Could not read duration", "file": file_path}

    segment_len = duration / num_segments
    peaks = []

    for i in range(num_segments):
        start = i * segment_len
        cmd = [
            "ffmpeg", "-ss", str(start), "-t", str(segment_len),
            "-i", file_path,
            "-af", "volumedetect",
            "-vn", "-f", "null", "/dev/null"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        m = re.search(r"mean_volume:\s*([-\d.]+)", result.stderr)
        db = float(m.group(1)) if m else -60.0
        peaks.append({
            "time": round(start, 2),
            "end_time": round(start + segment_len, 2),
            "db": db,
            "energy": _classify_energy(db),
        })

    # Find top 5 energetic moments
    sorted_peaks = sorted(peaks, key=lambda x: x["db"], reverse=True)
    best_moments = [p["time"] for p in sorted_peaks[:5]]

    return {
        "file": file_path,
        "duration": duration,
        "segments": peaks,
        "best_moments": best_moments,
        "peak_db": max(p["db"] for p in peaks),
        "valley_db": min(p["db"] for p in peaks),
    }


def detect_silence_ranges(file_path: str, silence_threshold_db: float = -35.0,
                           min_silence_duration: float = 0.5) -> dict:
    """
    Use FFmpeg silencedetect to find exact silence ranges in a file.
    Returns list of {start, end, duration} silence windows.
    """
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", f"silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration}",
        "-f", "null", "/dev/null"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stderr

    silences = []
    starts = re.findall(r"silence_start:\s*([\d.]+)", output)
    ends = re.findall(r"silence_end:\s*([\d.]+)", output)
    durations = re.findall(r"silence_duration:\s*([\d.]+)", output)

    for i, (s, e, d) in enumerate(zip(starts, ends, durations)):
        silences.append({
            "start": float(s),
            "end": float(e),
            "duration": float(d),
        })

    return {
        "file": file_path,
        "silence_count": len(silences),
        "total_silence_seconds": sum(s["duration"] for s in silences),
        "silences": silences,
    }


# ─────────────────────────────────────────────
#  CLIP SCORING
# ─────────────────────────────────────────────

def score_clips(timeline_info: dict) -> dict:
    """
    Score clips based on name keywords, duration, position.
    Returns ranked list with editorial notes.
    Gives Claude a starting point for keeper/reject decisions.
    """
    scored = []
    for track in timeline_info.get("video_tracks", []):
        track_num = track["track"]
        clips = track.get("clips", [])
        total_clips = len(clips)

        for i, clip in enumerate(clips):
            name = clip["name"].lower()
            dur = clip["duration"]
            score = 50  # baseline
            notes = []

            # Duration scoring
            if 2 <= dur <= 8:
                score += 15
                notes.append("good duration")
            elif dur < 0.5:
                score -= 30
                notes.append("too short — likely dead air")
            elif dur > 30:
                score -= 10
                notes.append("very long — consider trimming")

            # Name-based heuristics
            keep_keywords = ["hero", "best", "keep", "select", "v1", "final", "good", "great", "wide", "establishing", "beauty"]
            cut_keywords = ["bad", "ng", "cut", "delete", "remove", "silence", "blank", "black", "duplicate", "copy"]
            broll_keywords = ["broll", "b-roll", "b roll", "cutaway", "insert", "detail", "close", "cu ", "detail"]
            interview_keywords = ["interview", "talking head", "sync", "dialogue", "interview"]

            for kw in keep_keywords:
                if kw in name:
                    score += 20
                    notes.append(f"keyword: {kw}")
                    break
            for kw in cut_keywords:
                if kw in name:
                    score -= 25
                    notes.append(f"flagged: {kw}")
                    break
            for kw in broll_keywords:
                if kw in name:
                    notes.append("b-roll candidate")
                    break
            for kw in interview_keywords:
                if kw in name:
                    notes.append("dialogue/interview clip")
                    break

            # Position bonus — first and last clips matter
            if i == 0:
                notes.append("opening shot")
            if i == total_clips - 1:
                notes.append("closing shot")

            # File extension hints
            if ".r3d" in name or ".braw" in name or ".arri" in name:
                score += 5
                notes.append("raw camera original")

            scored.append({
                "track": track_num,
                "index": i,
                "name": clip["name"],
                "start": clip["start"],
                "end": clip["end"],
                "duration": dur,
                "score": max(0, min(100, score)),
                "notes": notes,
                "recommendation": "keep" if score >= 55 else "review" if score >= 35 else "cut",
            })

    scored.sort(key=lambda x: x["score"], reverse=True)

    keepers = [c for c in scored if c["recommendation"] == "keep"]
    reviews = [c for c in scored if c["recommendation"] == "review"]
    cuts = [c for c in scored if c["recommendation"] == "cut"]

    return {
        "total_clips": len(scored),
        "keepers": len(keepers),
        "for_review": len(reviews),
        "suggested_cuts": len(cuts),
        "ranked_clips": scored,
        "top_5": scored[:5],
        "bottom_5": scored[-5:] if len(scored) >= 5 else scored,
    }


def generate_chapter_markers(timeline_info: dict) -> dict:
    """
    Generate YouTube-style chapter timestamps from timeline markers.
    Returns formatted string ready to paste into YouTube description.
    """
    markers = timeline_info.get("markers", [])
    if not markers:
        return {"chapters": [], "youtube_format": "No markers found — add markers with names to generate chapters."}

    # Sort by time
    sorted_markers = sorted(markers, key=lambda m: m["time"])
    chapters = []
    lines = []

    for m in sorted_markers:
        t = m["time"]
        name = m.get("name", "") or m.get("note", "") or "Chapter"
        if not name.strip():
            continue
        mins = int(t // 60)
        secs = int(t % 60)
        timestamp = f"{mins}:{secs:02d}"
        chapters.append({"time": t, "timestamp": timestamp, "name": name})
        lines.append(f"{timestamp} {name}")

    # YouTube requires first chapter at 0:00
    if chapters and chapters[0]["time"] > 0:
        lines.insert(0, "0:00 Intro")

    return {
        "chapters": chapters,
        "youtube_format": "\n".join(lines),
        "count": len(chapters),
    }


def analyze_hook_strength(timeline_info: dict) -> dict:
    """
    Analyze the first 3-5 seconds of the edit for social media hook strength.
    Returns assessment and suggestions.
    """
    first_clips = []
    for track in timeline_info.get("video_tracks", []):
        for clip in track.get("clips", []):
            if clip["start"] < 5.0:
                first_clips.append(clip)
        break  # only track 1

    if not first_clips:
        return {"error": "No clips in first 5 seconds"}

    hook_duration = sum(c["duration"] for c in first_clips if c["start"] < 5.0)
    clip_names = [c["name"] for c in first_clips]

    issues = []
    strengths = []

    if hook_duration > 4:
        issues.append("Opening shot is too long — viewers may drop off before 3s")
    else:
        strengths.append("Tight opening cut — good for retention")

    for name in clip_names:
        n = name.lower()
        if any(x in n for x in ["wide", "establishing", "aerial", "drone"]):
            issues.append(f"'{name}' — wide/aerial shots are weak openers; start with a close-up or action")
        if any(x in n for x in ["logo", "title", "slate", "black", "color bars"]):
            issues.append(f"'{name}' — never open with logos/slates on social media")
        if any(x in n for x in ["action", "hero", "close", "cu", "reaction", "face"]):
            strengths.append(f"'{name}' — strong hook material")

    score = 70
    score -= len(issues) * 15
    score += len(strengths) * 10
    score = max(0, min(100, score))

    return {
        "hook_score": score,
        "hook_duration_seconds": hook_duration,
        "first_clips": clip_names,
        "strengths": strengths,
        "issues": issues,
        "recommendation": (
            "Strong hook — keep as is" if score >= 70 else
            "Decent hook — minor tweaks suggested" if score >= 45 else
            "Weak hook — consider reordering opening"
        ),
    }


# ─────────────────────────────────────────────
#  SMART ASSEMBLY
# ─────────────────────────────────────────────

# Brief keyword → clip affinity scoring
_BRIEF_KEYWORDS = {
    "energy": ["action", "run", "jump", "fast", "sport", "move", "hero", "power", "intense"],
    "emotional": ["face", "reaction", "close", "cu", "portrait", "interview", "tear", "smile", "look"],
    "cinematic": ["wide", "aerial", "drone", "establishing", "landscape", "beauty", "slow", "golden"],
    "corporate": ["office", "team", "meeting", "work", "business", "product", "logo", "brand"],
    "social": ["story", "reel", "tiktok", "short", "vertical", "quick", "hook", "grab"],
    "documentary": ["interview", "broll", "b-roll", "talking", "dialogue", "cutaway", "scene"],
    "music_video": ["performance", "concert", "stage", "artist", "dance", "beat", "rhythm"],
}

_NARRATIVE_ARCS = {
    "hype":       [0.3, 0.5, 0.8, 1.0, 0.9],   # energy curve per section
    "emotional":  [0.4, 0.6, 0.9, 0.7, 0.5],
    "corporate":  [0.5, 0.6, 0.7, 0.8, 0.7],
    "documentary":[0.4, 0.5, 0.7, 0.9, 0.6],
    "balanced":   [0.5, 0.6, 0.7, 0.8, 0.6],
}


def plan_assembly_from_brief(
    media_pool_clips: list,
    brief: str,
    target_duration: float = 60.0,
    style: str = "balanced",
) -> dict:
    """
    Given media pool clips and a creative brief, return an ordered assembly plan.
    
    brief: e.g. "60s hype reel that builds energy, starts wide then gets intense"
    style: hype | emotional | corporate | documentary | balanced
    target_duration: total edit length in seconds
    
    Returns ordered clip list with timing, narrative arc, and grade suggestions.
    """
    brief_lower = brief.lower()

    # Auto-detect style from brief if not specified
    if style == "balanced":
        for s in ["hype", "emotional", "corporate", "documentary"]:
            if s in brief_lower:
                style = s
                break
        if "music video" in brief_lower or "music vid" in brief_lower:
            style = "hype"
        if "social" in brief_lower or "reel" in brief_lower or "instagram" in brief_lower:
            style = "hype"

    # Score each clip against the brief
    scored = []
    for clip in media_pool_clips:
        name = (clip.get("name") or clip.get("file_name") or "").lower()
        path = (clip.get("file_path") or "").lower()
        combined = name + " " + path

        score = 50
        tags = []

        # Match brief keywords to clip names
        for category, keywords in _BRIEF_KEYWORDS.items():
            if category in brief_lower:
                for kw in keywords:
                    if kw in combined:
                        score += 20
                        tags.append(f"matches:{kw}")
                        break

        # Duration scoring — prefer clips in useful range
        dur = clip.get("duration", 0) or clip.get("clip_duration", 0)
        if 2 <= dur <= 10:
            score += 15
            tags.append("good_length")
        elif dur < 1:
            score -= 40
            tags.append("too_short")
        elif dur > 60:
            score -= 10
            tags.append("very_long")

        # Direct brief word match
        for word in brief_lower.split():
            if len(word) > 3 and word in combined:
                score += 15
                tags.append(f"brief_match:{word}")

        # Style affinity
        if style == "hype":
            for kw in ["action", "fast", "hero", "sport", "move", "energy", "power"]:
                if kw in combined:
                    score += 10
                    break
        elif style == "emotional":
            for kw in ["face", "reaction", "close", "cu", "portrait"]:
                if kw in combined:
                    score += 10
                    break
        elif style == "cinematic":
            for kw in ["wide", "aerial", "drone", "landscape", "beauty"]:
                if kw in combined:
                    score += 10
                    break

        scored.append({
            **clip,
            "assembly_score": max(0, min(100, score)),
            "tags": tags,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["assembly_score"], reverse=True)

    # Determine how many clips we need
    arc = _NARRATIVE_ARCS.get(style, _NARRATIVE_ARCS["balanced"])
    num_sections = len(arc)
    avg_clip_dur = target_duration / max(len(scored), 1) if scored else 3.0
    avg_clip_dur = max(1.5, min(8.0, avg_clip_dur))
    num_clips_needed = max(3, int(target_duration / avg_clip_dur))

    # Select top clips, enough to fill the target duration
    candidates = [c for c in scored if c["assembly_score"] > 20][:num_clips_needed * 2]
    if not candidates:
        return {"error": "No suitable clips found in media pool for this brief"}

    # Arrange clips according to narrative arc
    # Divide candidates into sections and pick best per section
    section_size = max(1, len(candidates) // num_sections)
    ordered = []
    cursor = 0.0

    for i, energy in enumerate(arc):
        section_clips = candidates[i * section_size:(i + 1) * section_size]
        if not section_clips:
            section_clips = candidates[:1]

        # For high-energy sections, prefer shorter clips; low-energy → longer
        clip_dur = avg_clip_dur * (0.6 if energy > 0.7 else 1.2 if energy < 0.5 else 1.0)
        clip_dur = round(max(1.0, min(8.0, clip_dur)), 2)

        for clip in section_clips[:max(1, num_clips_needed // num_sections)]:
            if cursor >= target_duration:
                break
            ordered.append({
                "name": clip.get("name") or clip.get("file_name"),
                "file_path": clip.get("file_path"),
                "suggested_duration": clip_dur,
                "timeline_start": round(cursor, 2),
                "timeline_end": round(cursor + clip_dur, 2),
                "section": i + 1,
                "energy_level": energy,
                "score": clip["assembly_score"],
            })
            cursor += clip_dur

    # Grade suggestion based on style
    grade_suggestions = {
        "hype":       {"contrast": 1.12, "saturation": 1.1,  "lift_b": 0.0,  "gain_r": 0.02, "note": "High contrast, punchy, slightly warm highlights"},
        "emotional":  {"contrast": 1.05, "saturation": 0.85, "lift_b": 0.02, "gain_r": 0.01, "note": "Desaturated, blue-tinted shadows, soft contrast"},
        "corporate":  {"contrast": 1.05, "saturation": 1.0,  "lift_b": 0.0,  "gain_r": 0.0,  "note": "Clean, neutral, professional"},
        "documentary":{"contrast": 1.08, "saturation": 0.9,  "lift_b": 0.01, "gain_r": 0.01, "note": "Slightly warm, naturalistic"},
        "balanced":   {"contrast": 1.06, "saturation": 0.95, "lift_b": 0.01, "gain_r": 0.01, "note": "Cinematic, slightly desaturated, blue shadows"},
    }

    return {
        "success": True,
        "brief": brief,
        "style": style,
        "target_duration": target_duration,
        "clips_in_pool": len(media_pool_clips),
        "clips_selected": len(ordered),
        "assembly_plan": ordered,
        "narrative_arc": arc,
        "grade_suggestion": grade_suggestions.get(style, grade_suggestions["balanced"]),
        "next_steps": [
            "Call assemble_clips_to_timeline with the assembly_plan to build the edit",
            "Then call color_grade_all_clips with the grade_suggestion values",
            "Then call auto_duck_music if there is a music track",
            "Then call normalize_all_audio",
        ],
    }
