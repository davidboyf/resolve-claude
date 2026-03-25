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


# ─────────────────────────────────────────────
#  DUPLICATE DETECTION
# ─────────────────────────────────────────────

def detect_duplicate_clips(timeline_info: dict) -> dict:
    """
    Find clips that appear more than once on the timeline.
    Groups by name similarity and flags which instance to keep (best scored).
    Returns actionable list: keep these, delete these.
    """
    from collections import defaultdict

    all_clips = []
    for track in timeline_info.get("video_tracks", []):
        for i, clip in enumerate(track.get("clips", [])):
            all_clips.append({
                **clip,
                "track": track["track"],
                "index": i,
            })

    # Group by normalized name (strip numbers, underscores, extensions)
    def normalize(name):
        import re
        n = re.sub(r'\.\w{2,4}$', '', name)          # remove extension
        n = re.sub(r'[_\-\s]+', ' ', n).strip().lower()
        n = re.sub(r'\s+\d+$', '', n)                 # strip trailing numbers
        return n

    groups = defaultdict(list)
    for clip in all_clips:
        key = normalize(clip["name"])
        groups[key].append(clip)

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        return {
            "duplicates_found": 0,
            "message": "No duplicate clips detected on the timeline.",
            "groups": [],
        }

    result_groups = []
    total_to_remove = 0

    for name_key, instances in duplicates.items():
        # Score each instance: longer trim = more intentional use; earlier position = better for narrative
        scored_instances = []
        for inst in instances:
            score = 50
            dur = inst.get("duration", 0)
            start = inst.get("start", 0)
            # Prefer moderate duration (well-trimmed)
            if 2 <= dur <= 8:
                score += 20
            elif dur < 1:
                score -= 30
            # Prefer earlier placement (likely the first considered use)
            score -= start * 0.1
            scored_instances.append({**inst, "keep_score": round(score, 1)})

        scored_instances.sort(key=lambda x: x["keep_score"], reverse=True)
        keeper = scored_instances[0]
        removals = scored_instances[1:]
        total_to_remove += len(removals)

        result_groups.append({
            "clip_name": instances[0]["name"],
            "normalized_key": name_key,
            "instance_count": len(instances),
            "keep": {
                "track": keeper["track"],
                "index": keeper["index"],
                "start": keeper.get("start"),
                "duration": keeper.get("duration"),
                "keep_score": keeper["keep_score"],
            },
            "remove": [
                {
                    "track": r["track"],
                    "index": r["index"],
                    "start": r.get("start"),
                    "duration": r.get("duration"),
                }
                for r in removals
            ],
        })

    return {
        "duplicates_found": len(duplicates),
        "total_to_remove": total_to_remove,
        "groups": result_groups,
        "summary": f"Found {len(duplicates)} duplicate clip groups. {total_to_remove} instances can be removed.",
    }


# ─────────────────────────────────────────────
#  FULL EDIT PLAN
# ─────────────────────────────────────────────

def build_full_edit_plan(timeline_info: dict, brief: str = "",
                          target_duration: float = None,
                          music_path: str = None,
                          style: str = "balanced") -> dict:
    """
    Analyze the timeline and return a complete, ordered edit plan.
    Claude should execute each step in sequence using the appropriate tools.
    This is the brain behind Full Edit Mode.
    """
    scores = score_clips(timeline_info)
    hook = analyze_hook_strength(timeline_info)
    dupes = detect_duplicate_clips(timeline_info)

    video_tracks = timeline_info.get("video_tracks", [])
    all_clips = []
    for t in video_tracks:
        all_clips.extend(t.get("clips", []))

    total_clips = len(all_clips)
    current_duration = timeline_info.get("duration", 0)
    fps = timeline_info.get("fps", 24)

    # Estimate issues
    issues = []
    short_clips = [c for c in all_clips if c.get("duration", 0) < 0.75]
    long_clips = [c for c in all_clips if c.get("duration", 0) > 15]
    cut_clips = [c for c in scores["ranked_clips"] if c["recommendation"] == "cut"]

    if dupes["duplicates_found"] > 0:
        issues.append(f"{dupes['duplicates_found']} duplicate clip groups — {dupes['total_to_remove']} can be removed")
    if short_clips:
        issues.append(f"{len(short_clips)} clips under 0.75s — likely dead air")
    if hook["hook_score"] < 60:
        issues.append(f"Weak hook (score {hook['hook_score']}/100) — {'; '.join(hook['issues'][:2])}")
    if cut_clips:
        issues.append(f"{len(cut_clips)} clips scored as 'cut' candidates")
    if long_clips:
        issues.append(f"{len(long_clips)} clips over 15s — consider trimming")

    # Build ordered step list
    steps = []
    step_num = 1

    def add_step(action, tool, args_description, reason, priority="normal"):
        steps.append({
            "step": step_num,
            "action": action,
            "tool": tool,
            "args": args_description,
            "reason": reason,
            "priority": priority,
        })

    # Step 1: Always start with full analysis
    add_step("Read timeline", "get_timeline_info", {}, "Confirm current state", "required")
    step_num += 1

    # Step 2: Remove duplicates if found
    if dupes["duplicates_found"] > 0:
        for group in dupes["groups"]:
            for removal in group["remove"]:
                add_step(
                    f"Remove duplicate: {group['clip_name']}",
                    "ripple_delete_clip",
                    {"track": removal["track"], "clip_index": removal["index"]},
                    f"Keeping best instance at {group['keep']['start']:.1f}s",
                    "high",
                )
                step_num += 1

    # Step 3: Remove dead air / flagged clips
    if short_clips or cut_clips:
        add_step(
            "Flag and clean dead air",
            "detect_and_cut_silence",
            {"track": 1, "min_duration_seconds": 0.75},
            "Remove clips shorter than 0.75s",
            "high",
        )
        step_num += 1

    # Step 4: Remove all gaps
    add_step("Close all gaps", "ripple_delete_all_gaps",
             {"track": 1}, "Tighten edit after removals", "high")
    step_num += 1

    # Step 5: Fix hook if weak
    if hook["hook_score"] < 60 and scores["ranked_clips"]:
        best_clip = scores["ranked_clips"][0]
        add_step(
            "Strengthen opening",
            "move_clip_to_position",
            {"track": best_clip["track"], "clip_index": best_clip["index"], "new_start_seconds": 0},
            f"Move '{best_clip['name']}' (score {best_clip['score']}) to position 0 for stronger hook",
            "high",
        )
        step_num += 1

    # Step 6: Trim to target if specified
    if target_duration and current_duration > target_duration * 1.1:
        add_step(
            f"Trim to {target_duration}s",
            "smart_trim_to_duration",
            {"target_seconds": target_duration, "strategy": "remove_short"},
            f"Edit is {current_duration:.0f}s, target is {target_duration:.0f}s",
            "high",
        )
        step_num += 1

    # Step 7: Rough cut pass
    avg_dur = current_duration / max(total_clips, 1)
    target_clip_dur = min(max(avg_dur * 0.7, 2.0), 6.0)
    add_step(
        "Rough cut pass",
        "auto_rough_cut",
        {"track": 1, "target_duration_seconds": round(target_clip_dur, 1)},
        f"Trim clips to ~{target_clip_dur:.1f}s avg for better pacing",
        "normal",
    )
    step_num += 1

    # Step 8: Beat sync if music provided
    if music_path:
        add_step(
            "Detect beats",
            "detect_beats",
            {"file_path": music_path},
            "Get beat timestamps for sync cutting",
            "high",
        )
        step_num += 1
        add_step(
            "Cut to beat",
            "cut_clips_at_beats",
            {"beat_times": "[use every_2 or every_4 beats from detect_beats result]", "track": 1},
            "Sync cuts to music rhythm",
            "high",
        )
        step_num += 1

    # Step 9: Visual dynamics
    add_step(
        "Add zoom variation",
        "set_clip_zoom_all",
        {"track": 1, "scale": 1.12, "alternate": True},
        "Add subtle punch-in/pan variation across all clips for dynamic feel",
        "normal",
    )
    step_num += 1

    # Step 10: Speed ramp on best clip
    if scores["ranked_clips"]:
        hero = scores["ranked_clips"][0]
        add_step(
            f"Speed ramp hero clip: {hero['name']}",
            "apply_speed_ramp",
            {"track": hero["track"], "clip_index": hero["index"],
             "ramp_points": [{"position": 0.0, "speed": 1.0},
                             {"position": 0.4, "speed": 0.3},
                             {"position": 0.7, "speed": 0.3},
                             {"position": 1.0, "speed": 1.0}]},
            "Dramatic slow-motion on the strongest clip",
            "normal",
        )
        step_num += 1

    # Step 11: Grade
    grade_map = {
        "hype":       {"contrast": 1.12, "saturation": 1.05, "lift_b": 0.0,  "gain_r": 0.02, "gain_b": -0.01},
        "emotional":  {"contrast": 1.05, "saturation": 0.82, "lift_b": 0.03, "gain_r": 0.01, "gain_b": 0.0},
        "corporate":  {"contrast": 1.04, "saturation": 1.0,  "lift_b": 0.0,  "gain_r": 0.0,  "gain_b": 0.0},
        "documentary":{"contrast": 1.07, "saturation": 0.9,  "lift_b": 0.01, "gain_r": 0.01, "gain_b": 0.0},
        "balanced":   {"contrast": 1.07, "saturation": 0.93, "lift_b": 0.02, "gain_r": 0.01, "gain_b": -0.01},
    }
    grade = grade_map.get(style, grade_map["balanced"])
    add_step(
        "Grade all clips",
        "color_grade_all_clips",
        {**grade, "track": 1},
        f"Apply consistent {style} grade across entire edit",
        "normal",
    )
    step_num += 1

    # Step 12: Add cross dissolves
    add_step(
        "Add transitions",
        "apply_cross_dissolve_all",
        {"track": 1, "duration_seconds": 0.4},
        "Smooth cuts with short dissolves",
        "normal",
    )
    step_num += 1

    # Step 13: Audio pass
    audio_tracks = timeline_info.get("audio_tracks", [])
    if len(audio_tracks) >= 2:
        add_step(
            "Duck music under dialogue",
            "auto_duck_music",
            {"dialogue_track": 1, "music_track": 2, "normal_music_db": -18.0, "duck_db": -30.0},
            "Lower music wherever dialogue exists",
            "normal",
        )
        step_num += 1

    add_step(
        "Normalize all audio",
        "normalize_all_audio",
        {"track": 1, "target_db": -12.0},
        "Broadcast-level audio across all clips",
        "normal",
    )
    step_num += 1

    # Step 14: Final check
    add_step(
        "Final hook check",
        "analyze_hook_strength",
        {"timeline_info": "[call get_timeline_info() first]"},
        "Verify opening is strong after edits",
        "normal",
    )
    step_num += 1
    add_step(
        "Export edit summary",
        "export_edit_summary",
        {"track": 1},
        "Generate final report of the completed edit",
        "normal",
    )
    step_num += 1

    return {
        "success": True,
        "brief": brief or "Full professional edit",
        "style": style,
        "current_duration": round(current_duration, 2),
        "target_duration": target_duration,
        "total_clips": total_clips,
        "issues_found": issues,
        "total_steps": len(steps),
        "steps": steps,
        "duplicate_report": dupes,
        "hook_report": hook,
        "clip_scores": scores["ranked_clips"][:10],
        "instruction": (
            "Execute each step in order using the specified tools. "
            "After each destructive step (delete/trim), call get_timeline_info() to confirm state. "
            "Report progress after every 3-4 steps."
        ),
    }
