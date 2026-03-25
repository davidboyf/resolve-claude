"""
DaVinci Resolve Python API Bridge
Wraps all Resolve operations for use as Claude tools.
"""
import os
import sys
import json
from typing import Optional, Any

# Set up Resolve scripting paths
_RESOLVE_API = os.environ.get(
    "RESOLVE_SCRIPT_API",
    "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
)
_RESOLVE_LIB = os.environ.get(
    "RESOLVE_SCRIPT_LIB",
    "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
)

sys.path.insert(0, os.path.join(_RESOLVE_API, "Modules"))


def _get_resolve():
    try:
        import DaVinciResolveScript as dvr
        r = dvr.scriptapp("Resolve")
        if r is None:
            raise ConnectionError("DaVinci Resolve is not running or scripting is disabled.")
        return r
    except ImportError:
        raise ImportError(
            "Cannot import DaVinciResolveScript. Make sure DaVinci Resolve is open "
            "and scripting is enabled under Preferences → General → External scripting."
        )


def _fps(timeline) -> float:
    """Return timeline FPS as float."""
    setting = timeline.GetSetting("timelineFrameRate")
    try:
        return float(setting)
    except Exception:
        return 24.0


# ─────────────────────────────────────────────
#  STATUS / PROJECT
# ─────────────────────────────────────────────

def get_status() -> dict:
    """Check if Resolve is running and return project info."""
    try:
        resolve = _get_resolve()
        pm = resolve.GetProjectManager()
        project = pm.GetCurrentProject()
        if not project:
            return {"connected": True, "project": None, "timeline": None}

        timeline = project.GetCurrentTimeline()
        return {
            "connected": True,
            "project": project.GetName(),
            "timeline": timeline.GetName() if timeline else None,
            "fps": _fps(timeline) if timeline else None,
            "resolve_version": resolve.GetVersionString(),
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}


def get_project_info() -> dict:
    resolve = _get_resolve()
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    timelines = []
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        timelines.append({"name": t.GetName(), "index": i})
    return {
        "name": project.GetName(),
        "timelines": timelines,
        "current_timeline": project.GetCurrentTimeline().GetName(),
        "render_presets": project.GetRenderPresetList(),
    }


# ─────────────────────────────────────────────
#  TIMELINE
# ─────────────────────────────────────────────

def get_timeline_info() -> dict:
    """Get full timeline structure with all clips and tracks."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)

    video_tracks = []
    for i in range(1, timeline.GetTrackCount("video") + 1):
        clips = []
        for clip in (timeline.GetItemListInTrack("video", i) or []):
            clips.append({
                "name": clip.GetName(),
                "start": clip.GetStart() / fps,
                "end": clip.GetEnd() / fps,
                "duration": clip.GetDuration() / fps,
                "start_frame": clip.GetStart(),
                "end_frame": clip.GetEnd(),
                "clip_color": clip.GetClipColor(),
            })
        video_tracks.append({"track": i, "clips": clips})

    audio_tracks = []
    for i in range(1, timeline.GetTrackCount("audio") + 1):
        clips = []
        for clip in (timeline.GetItemListInTrack("audio", i) or []):
            clips.append({
                "name": clip.GetName(),
                "start": clip.GetStart() / fps,
                "end": clip.GetEnd() / fps,
            })
        audio_tracks.append({"track": i, "clips": clips})

    return {
        "name": timeline.GetName(),
        "fps": fps,
        "duration": timeline.GetEndFrame() / fps,
        "start_frame": timeline.GetStartFrame(),
        "end_frame": timeline.GetEndFrame(),
        "video_tracks": video_tracks,
        "audio_tracks": audio_tracks,
        "markers": get_markers(),
    }


def get_markers() -> list:
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    raw = timeline.GetMarkers() or {}
    return [
        {
            "frame": frame,
            "time": frame / fps,
            "color": data.get("color", "Blue"),
            "name": data.get("name", ""),
            "note": data.get("note", ""),
            "duration": data.get("duration", 1),
        }
        for frame, data in raw.items()
    ]


def add_marker(time_seconds: float, color: str = "Blue", name: str = "", note: str = "") -> dict:
    """Add a marker at a specific time. Colors: Red, Green, Blue, Cyan, Magenta, Yellow, White."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    frame = int(time_seconds * fps)
    ok = timeline.AddMarker(frame, color, name, note, 1)
    return {"success": ok, "frame": frame, "time": time_seconds, "color": color, "name": name}


def delete_marker(time_seconds: float) -> dict:
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    frame = int(time_seconds * fps)
    ok = timeline.DeleteMarkerAtFrame(frame)
    return {"success": ok, "frame": frame}


def set_playhead(time_seconds: float) -> dict:
    """Move the playhead to a specific time."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    frame = int(time_seconds * fps) + timeline.GetStartFrame()
    timeline.SetCurrentTimecode(str(frame))
    return {"success": True, "time": time_seconds, "frame": frame}


def split_clip_at(time_seconds: float, track: int = 1) -> dict:
    """Split/razor a clip at the given time on a video track."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)

    clips = timeline.GetItemListInTrack("video", track) or []
    frame = int(time_seconds * fps)
    target = None
    for clip in clips:
        if clip.GetStart() <= frame < clip.GetEnd():
            target = clip
            break

    if not target:
        return {"success": False, "error": f"No clip found at {time_seconds}s on track {track}"}

    # Use Split method if available (Resolve 18+)
    if hasattr(target, "Split"):
        ok = target.Split()
    else:
        # Fallback for older Resolve: use timeline's razor via SetCurrentTimecodeByFrame + action
        try:
            timeline.SetCurrentTimecodeByFrame(frame + timeline.GetStartFrame())
            # Attempt via project scripting API razor action
            ok = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline().Split()
        except Exception:
            ok = False

    return {"success": bool(ok), "time": time_seconds, "track": track}


def delete_clips_in_range(start_seconds: float, end_seconds: float, track: int = 1) -> dict:
    """Delete all clips in the given time range on a video track."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)

    clips = timeline.GetItemListInTrack("video", track) or []
    start_frame = int(start_seconds * fps)
    end_frame = int(end_seconds * fps)

    deleted = []
    for clip in clips:
        if clip.GetStart() >= start_frame and clip.GetEnd() <= end_frame:
            clip_name = clip.GetName()
            timeline.DeleteClips([clip])
            deleted.append(clip_name)

    return {"success": True, "deleted": deleted, "range": [start_seconds, end_seconds]}


def set_clip_color(clip_name: str, color: str, track: int = 1) -> dict:
    """Set a clip's label color. Colors: Orange, Apricot, Yellow, Lime, Olive, Green, Teal, Navy, Blue, Purple, Violet, Pink, Tan, Beige, Brown, Chocolate."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    for clip in clips:
        if clip.GetName() == clip_name:
            clip.SetClipColor(color)
            return {"success": True, "clip": clip_name, "color": color}
    return {"success": False, "error": f"Clip '{clip_name}' not found on track {track}"}


def add_clip_to_timeline(media_path: str, start_seconds: float = 0.0, end_seconds: Optional[float] = None) -> dict:
    """Add a media file to the current timeline."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    media_pool = project.GetMediaPool()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)

    items = media_pool.ImportMedia([media_path])
    if not items:
        return {"success": False, "error": f"Could not import: {media_path}"}

    clip_info = {"mediaPoolItem": items[0]}
    if start_seconds:
        clip_info["startFrame"] = int(start_seconds * fps)
    if end_seconds:
        clip_info["endFrame"] = int(end_seconds * fps)

    ok = media_pool.AppendToTimeline([clip_info])
    return {"success": bool(ok), "path": media_path}


# ─────────────────────────────────────────────
#  COLOR GRADING
# ─────────────────────────────────────────────

def get_clip_color_info(track: int = 1, clip_index: int = 0) -> dict:
    """Get color grade info for a clip."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip index out of range"}

    clip = clips[clip_index]
    # Switch to color page to access grade
    resolve.OpenPage("color")
    timeline.SetCurrentTimecodeByFrame(clip.GetStart())

    return {
        "clip": clip.GetName(),
        "track": track,
        "index": clip_index,
        "message": "Switched to Color page, clip selected.",
    }


def apply_color_wheel(
    wheel: str,
    red: float = 0.0,
    green: float = 0.0,
    blue: float = 0.0,
    luma: float = 0.0,
    track: int = 1,
    clip_index: int = 0,
) -> dict:
    """
    Adjust color wheels (Lift/Gamma/Gain/Offset) on the selected clip.
    wheel: 'lift' | 'gamma' | 'gain' | 'offset'
    Values: -1.0 to 1.0 (0 = no change)
    """
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}

    clip = clips[clip_index]
    resolve.OpenPage("color")

    wheel_map = {
        "lift": "ColorWheelLift",
        "gamma": "ColorWheelGamma",
        "gain": "ColorWheelGain",
        "offset": "ColorWheelOffset",
    }
    prop_name = wheel_map.get(wheel.lower())
    if not prop_name:
        return {"error": f"Unknown wheel '{wheel}'. Use: lift, gamma, gain, offset"}

    clip.SetProperty(prop_name, {"Red": red, "Green": green, "Blue": blue, "Luma": luma})
    return {
        "success": True,
        "clip": clip.GetName(),
        "wheel": wheel,
        "values": {"red": red, "green": green, "blue": blue, "luma": luma},
    }


def apply_lut(lut_path: str, track: int = 1, clip_index: int = 0) -> dict:
    """Apply a .cube LUT file to a clip."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    ok = clip.SetLUT(1, lut_path)  # 1 = node index
    return {"success": ok, "lut": lut_path, "clip": clip.GetName()}


def set_contrast_saturation(
    contrast: float = 1.0,
    saturation: float = 1.0,
    track: int = 1,
    clip_index: int = 0,
) -> dict:
    """Set contrast (0.0-2.0, 1.0=normal) and saturation (0.0-2.0, 1.0=normal)."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    clip.SetProperty("Contrast", contrast)
    clip.SetProperty("Saturation", saturation)
    return {"success": True, "clip": clip.GetName(), "contrast": contrast, "saturation": saturation}


def add_serial_node(label: str = "New Node", track: int = 1, clip_index: int = 0) -> dict:
    """Add a new serial color correction node to a clip's node graph."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    graph = clip.GetNodeGraph()
    if not graph:
        return {"error": "Could not access node graph"}
    node = graph.AddNode("SerialNode")
    if node and label:
        node.SetLabel(label)
    return {"success": bool(node), "label": label, "clip": clip.GetName()}


def reset_grade(track: int = 1, clip_index: int = 0) -> dict:
    """Reset all color grading on a clip back to default."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    clip.ResetAllGrades()
    return {"success": True, "clip": clip.GetName()}


# ─────────────────────────────────────────────
#  AUDIO
# ─────────────────────────────────────────────

def set_audio_track_volume(track: int, volume_db: float) -> dict:
    """Set the volume of an audio track in dB (0 = unity, -∞ = mute)."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    ok = timeline.SetTrackEnable("audio", track, True)
    # Set volume via clip properties
    clips = timeline.GetItemListInTrack("audio", track) or []
    set_count = 0
    for clip in clips:
        clip.SetProperty("Volume", volume_db)
        set_count += 1
    return {"success": True, "track": track, "volume_db": volume_db, "clips_affected": set_count}


def mute_audio_track(track: int, muted: bool = True) -> dict:
    """Mute or unmute an audio track."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    ok = timeline.SetTrackEnable("audio", track, not muted)
    return {"success": ok, "track": track, "muted": muted}


def set_clip_audio_volume(clip_name: str, volume_db: float, audio_track: int = 1) -> dict:
    """Set volume on a specific audio clip."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("audio", audio_track) or []
    for clip in clips:
        if clip.GetName() == clip_name:
            clip.SetProperty("Volume", volume_db)
            return {"success": True, "clip": clip_name, "volume_db": volume_db}
    return {"success": False, "error": f"Audio clip '{clip_name}' not found"}


# ─────────────────────────────────────────────
#  RENDER / EXPORT
# ─────────────────────────────────────────────

def get_render_presets() -> list:
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    return project.GetRenderPresetList() or []


def start_render(preset_name: str, output_path: str) -> dict:
    """Start rendering with a specific preset to a given output path."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()

    project.LoadRenderPreset(preset_name)
    project.SetRenderSettings({"TargetDir": output_path})
    project.AddRenderJob()
    ok = project.StartRendering()
    return {
        "success": ok,
        "preset": preset_name,
        "output": output_path,
        "message": "Render started. Check Deliver page for progress.",
    }


def switch_page(page: str) -> dict:
    """Switch DaVinci Resolve to a specific page. Pages: media, cut, edit, fusion, color, fairlight, deliver"""
    valid = ["media", "cut", "edit", "fusion", "color", "fairlight", "deliver"]
    if page not in valid:
        return {"error": f"Invalid page '{page}'. Valid: {valid}"}
    resolve = _get_resolve()
    resolve.OpenPage(page)
    return {"success": True, "page": page}


# ─────────────────────────────────────────────
#  FUSION (VFX NODES)
# ─────────────────────────────────────────────

def open_fusion_for_clip(track: int = 1, clip_index: int = 0) -> dict:
    """Open the Fusion page for a specific clip to add VFX nodes."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("fusion")
    timeline.SetCurrentTimecodeByFrame(clip.GetStart())
    return {"success": True, "clip": clip.GetName(), "message": "Fusion page opened for clip."}


# ─────────────────────────────────────────────
#  MEDIA POOL
# ─────────────────────────────────────────────

def get_media_pool_clips() -> list:
    """List all clips in the media pool."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    media_pool = project.GetMediaPool()
    root = media_pool.GetRootFolder()

    def collect(folder):
        result = []
        for clip in (folder.GetClipList() or []):
            props = clip.GetClipProperty()
            result.append({
                "name": clip.GetName(),
                "duration": props.get("Duration", ""),
                "fps": props.get("FPS", ""),
                "resolution": f"{props.get('Video Width','?')}x{props.get('Video Height','?')}",
                "file_path": props.get("File Path", ""),
                "type": props.get("Type", ""),
            })
        for sub in (folder.GetSubFolderList() or []):
            result.extend(collect(sub))
        return result

    return collect(root)


# ─────────────────────────────────────────────
#  NEW: COLOR GRADE READ
# ─────────────────────────────────────────────

def get_clip_grade(track: int = 1, clip_index: int = 0) -> dict:
    """Read the current color grade values for a clip (wheels, contrast, saturation)."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")

    def safe_get(prop):
        try:
            return clip.GetProperty(prop)
        except Exception:
            return None

    return {
        "clip": clip.GetName(),
        "track": track,
        "index": clip_index,
        "lift":     safe_get("ColorWheelLift"),
        "gamma":    safe_get("ColorWheelGamma"),
        "gain":     safe_get("ColorWheelGain"),
        "offset":   safe_get("ColorWheelOffset"),
        "contrast":    safe_get("Contrast"),
        "saturation":  safe_get("Saturation"),
        "hue":         safe_get("Hue"),
        "luma_mix":    safe_get("LumaContribution"),
    }


# ─────────────────────────────────────────────
#  NEW: TIMELINE SWITCHING
# ─────────────────────────────────────────────

def list_timelines() -> list:
    """List all timelines in the current project."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    fps_val = None
    result = []
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        try:
            fps_val = float(t.GetSetting("timelineFrameRate"))
        except Exception:
            fps_val = None
        result.append({
            "index": i,
            "name": t.GetName(),
            "fps": fps_val,
            "is_current": t.GetName() == project.GetCurrentTimeline().GetName(),
        })
    return result


def switch_timeline(name: str) -> dict:
    """Switch the active timeline by name."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        if t.GetName() == name:
            ok = project.SetCurrentTimeline(t)
            return {"success": bool(ok), "timeline": name}
    return {"success": False, "error": f"Timeline '{name}' not found"}


# ─────────────────────────────────────────────
#  NEW: TRANSITIONS
# ─────────────────────────────────────────────

def add_transition(
    clip_index: int,
    transition_type: str = "Cross Dissolve",
    duration_frames: int = 24,
    position: str = "end",
    track: int = 1,
) -> dict:
    """
    Add a transition to a clip.
    transition_type: 'Cross Dissolve', 'Dip to Color Dissolve', 'Dip to Black'
    position: 'start' | 'end' | 'both'
    duration_frames: length of transition in frames
    """
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip index out of range"}

    clip = clips[clip_index]
    resolve.OpenPage("edit")

    results = []
    if position in ("end", "both") and clip_index + 1 < len(clips):
        ok = timeline.AddTransition(transition_type, clip, clips[clip_index + 1], duration_frames)
        results.append({"edge": "end", "success": bool(ok)})
    if position in ("start", "both") and clip_index > 0:
        ok = timeline.AddTransition(transition_type, clips[clip_index - 1], clip, duration_frames)
        results.append({"edge": "start", "success": bool(ok)})
    if not results:
        return {"success": False, "error": "No adjacent clips to add transition to"}

    return {
        "success": any(r["success"] for r in results),
        "transitions": results,
        "type": transition_type,
        "duration_frames": duration_frames,
    }


# ─────────────────────────────────────────────
#  NEW: COPY GRADE
# ─────────────────────────────────────────────

def copy_grade_to_clips(
    source_track: int = 1,
    source_clip_index: int = 0,
    target_track: int = 1,
    target_clip_indices: Optional[list] = None,
) -> dict:
    """Copy the color grade from one clip to one or more other clips."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()

    src_clips = timeline.GetItemListInTrack("video", source_track) or []
    if source_clip_index >= len(src_clips):
        return {"error": "Source clip not found"}

    source_clip = src_clips[source_clip_index]
    resolve.OpenPage("color")

    if target_clip_indices is None:
        target_clip_indices = []

    tgt_clips = timeline.GetItemListInTrack("video", target_track) or []
    copied = []
    failed = []

    for idx in target_clip_indices:
        if idx >= len(tgt_clips):
            failed.append({"index": idx, "reason": "out of range"})
            continue
        target_clip = tgt_clips[idx]
        try:
            # Copy via ApplyGradeFromVersion (Resolve Studio API)
            ok = target_clip.ApplyGradeFromVersion(source_clip, 0)
            if ok:
                copied.append(target_clip.GetName())
            else:
                failed.append({"index": idx, "reason": "API returned False"})
        except Exception as e:
            failed.append({"index": idx, "reason": str(e)})

    return {
        "success": len(copied) > 0,
        "source": source_clip.GetName(),
        "copied_to": copied,
        "failed": failed,
    }


# ─────────────────────────────────────────────
#  NEW: RENDER STATUS
# ─────────────────────────────────────────────

def get_render_status() -> dict:
    """Get the current render job queue and their statuses."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()

    is_rendering = project.IsRenderingInProgress()
    jobs = project.GetRenderJobList() or []

    job_list = []
    for job in jobs:
        job_id = job.get("JobId", "")
        status_info = project.GetRenderJobStatus(job_id) if job_id else {}
        job_list.append({
            "job_id": job_id,
            "timeline": job.get("TimelineName", ""),
            "preset": job.get("RenderPreset", ""),
            "output": job.get("TargetDir", ""),
            "status": status_info.get("JobStatus", "Unknown"),
            "completion": status_info.get("CompletionPercentage", 0),
            "error": status_info.get("Error", ""),
        })

    return {
        "is_rendering": is_rendering,
        "job_count": len(job_list),
        "jobs": job_list,
    }


def cancel_render() -> dict:
    """Stop all in-progress render jobs."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    ok = project.StopRendering()
    return {"success": bool(ok), "message": "Render stopped."}


def delete_render_job(job_id: str) -> dict:
    """Delete a render job from the queue by ID."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    ok = project.DeleteRenderJobByUniqueId(job_id)
    return {"success": bool(ok), "job_id": job_id}


# ─────────────────────────────────────────────
#  NEW: TRANSCRIBE AS RESOLVE TOOL
# ─────────────────────────────────────────────

def transcribe_clip_file(
    file_path: str,
    language: str = "en",
    model_size: str = "base",
) -> dict:
    """
    Transcribe a video/audio file using Whisper.
    Returns full transcript text + timestamped segments.
    Useful for deciding where to cut based on speech content.
    """
    from transcribe import transcribe, format_transcript_for_claude
    result = transcribe(file_path, language, model_size)
    result["formatted"] = format_transcript_for_claude(result)
    return result


def apply_transcript_markers(
    file_path: str,
    mode: str = "silence",
    language: str = "en",
    model_size: str = "base",
) -> dict:
    """
    Transcribe a file and auto-apply markers to the current timeline.
    mode='silence' — Red markers on gaps between speech segments (silence/dead air).
    mode='segments' — Blue markers at the start of each spoken segment.
    """
    from transcribe import transcribe

    result = transcribe(file_path, language, model_size)
    segments = result.get("segments", [])
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)

    added = []

    if mode == "segments":
        for seg in segments:
            frame = int(seg["start"] * fps) + timeline.GetStartFrame()
            text_snippet = seg["text"][:40].strip()
            ok = timeline.AddMarker(
                int(seg["start"] * fps), "Blue", "Speech", text_snippet, 1
            )
            if ok:
                added.append({"time": seg["start"], "text": text_snippet})

    elif mode == "silence":
        # Mark gaps > 0.5s between segments as silence
        prev_end = 0.0
        for seg in segments:
            gap = seg["start"] - prev_end
            if gap > 0.5:
                frame = int(prev_end * fps)
                ok = timeline.AddMarker(frame, "Red", "Silence", f"{gap:.1f}s gap", int(gap * fps))
                if ok:
                    added.append({"time": prev_end, "duration": gap})
            prev_end = seg["end"]

    return {
        "success": True,
        "mode": mode,
        "markers_added": len(added),
        "markers": added,
        "total_segments": len(segments),
        "duration": result.get("duration", 0),
    }


# ─────────────────────────────────────────────
#  NEW: SPEED RAMP
# ─────────────────────────────────────────────

def set_clip_speed(
    clip_index: int,
    speed_percent: float = 100.0,
    track: int = 1,
) -> dict:
    """Set the playback speed of a video clip. 100=normal, 50=half speed, 200=2x speed."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    ok = clip.SetProperty("Speed", speed_percent)
    return {
        "success": bool(ok),
        "clip": clip.GetName(),
        "speed_percent": speed_percent,
    }


# ─────────────────────────────────────────────
#  NEW: CLIP FLAGS
# ─────────────────────────────────────────────

def flag_clip(clip_index: int, flag_color: str = "Red", track: int = 1) -> dict:
    """Add a flag to a clip. flag_color: Red, Green, Blue, Cyan, Magenta, Yellow."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    clip.AddFlag(flag_color)
    return {"success": True, "clip": clip.GetName(), "flag": flag_color}


def unflag_clip(clip_index: int, flag_color: str = "Red", track: int = 1) -> dict:
    """Remove a flag from a clip."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    clip.ClearFlags(flag_color)
    return {"success": True, "clip": clip.GetName(), "flag": flag_color}


# ─────────────────────────────────────────────
#  SCREEN CAPTURE / VISUAL FEEDBACK
# ─────────────────────────────────────────────

def capture_screen() -> dict:
    """Take a screenshot so Claude can visually see what's on the DaVinci Resolve screen."""
    from screen_capture import capture_screen as _cap
    return _cap(window_only=False)


def grab_resolve_frame() -> dict:
    """Export the current Resolve timeline frame as an image for Claude to analyze."""
    from screen_capture import grab_resolve_frame as _grab
    return _grab()


def load_reference_image(path_or_url: str) -> dict:
    """Load a reference image from disk or URL for color matching analysis."""
    from screen_capture import load_image_as_base64
    return load_image_as_base64(path_or_url)


# ─────────────────────────────────────────────
#  ADVANCED NODE GRAPH
# ─────────────────────────────────────────────

def create_parallel_node(label: str = "Parallel", track: int = 1, clip_index: int = 0) -> dict:
    """Add a parallel color node to a clip's node graph."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    graph = clip.GetNodeGraph()
    if not graph:
        return {"error": "Cannot access node graph"}
    node = graph.AddNode("ParallelNode")
    if node and label:
        node.SetLabel(label)
    return {"success": bool(node), "label": label, "type": "parallel"}


def create_layer_node(label: str = "Layer", track: int = 1, clip_index: int = 0) -> dict:
    """Add a layer mixer node to a clip's node graph."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    graph = clip.GetNodeGraph()
    if not graph:
        return {"error": "Cannot access node graph"}
    node = graph.AddNode("LayerNode")
    if node and label:
        node.SetLabel(label)
    return {"success": bool(node), "label": label, "type": "layer"}


def set_node_curves(
    node_index: int = 1,
    curve_type: str = "custom",
    control_points: Optional[list] = None,
    track: int = 1,
    clip_index: int = 0,
) -> dict:
    """
    Set custom curve control points on a color node.
    curve_type: 'lum_vs_lum' | 'hue_vs_sat' | 'hue_vs_hue' | 'sat_vs_sat' | 'custom'
    control_points: list of [input, output] pairs, e.g. [[0,0],[0.5,0.6],[1,1]]
    """
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")

    if control_points is None:
        control_points = [[0, 0], [0.5, 0.5], [1, 1]]

    # Map curve type to Resolve property names
    curve_map = {
        "custom": "CurveCustom",
        "lum_vs_lum": "CurveLumVsLum",
        "hue_vs_sat": "CurveHueVsSat",
        "hue_vs_hue": "CurveHueVsHue",
        "sat_vs_sat": "CurveSatVsSat",
        "hue_vs_lum": "CurveHueVsLum",
    }
    prop = curve_map.get(curve_type, "CurveCustom")

    try:
        clip.SetProperty(prop, {"Points": control_points})
        return {
            "success": True,
            "clip": clip.GetName(),
            "curve_type": curve_type,
            "control_points": control_points,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_node_graph(track: int = 1, clip_index: int = 0) -> dict:
    """Get the color node graph structure for a clip."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    graph = clip.GetNodeGraph()
    if not graph:
        return {"error": "Cannot access node graph"}

    nodes = []
    try:
        for node in (graph.GetNodeList() or []):
            nodes.append({
                "label": node.GetLabel() if hasattr(node, "GetLabel") else "",
                "type": node.GetType() if hasattr(node, "GetType") else "Unknown",
            })
    except Exception:
        pass

    return {
        "clip": clip.GetName(),
        "track": track,
        "index": clip_index,
        "nodes": nodes,
        "node_count": len(nodes),
    }


def apply_hsl_qualifier(
    hue_center: float = 0.0,
    hue_width: float = 30.0,
    sat_min: float = 0.2,
    sat_max: float = 1.0,
    lum_min: float = 0.0,
    lum_max: float = 1.0,
    track: int = 1,
    clip_index: int = 0,
) -> dict:
    """
    Apply an HSL qualifier (secondary color correction selector) to a clip node.
    Useful for isolating specific colors (e.g., sky, skin tones, grass).
    hue_center: 0-360 (red=0, yellow=60, green=120, cyan=180, blue=240, magenta=300)
    hue_width: how wide the hue selection is (degrees)
    """
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    try:
        clip.SetProperty("QualifierHueLow", (hue_center - hue_width / 2) / 360.0)
        clip.SetProperty("QualifierHueHigh", (hue_center + hue_width / 2) / 360.0)
        clip.SetProperty("QualifierSatLow", sat_min)
        clip.SetProperty("QualifierSatHigh", sat_max)
        clip.SetProperty("QualifierLumLow", lum_min)
        clip.SetProperty("QualifierLumHigh", lum_max)
        return {
            "success": True,
            "clip": clip.GetName(),
            "hue_center": hue_center,
            "hue_width": hue_width,
            "message": f"HSL qualifier applied. Selecting hue ~{hue_center}° ±{hue_width/2}°",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
#  SCENE DETECTION
# ─────────────────────────────────────────────

def detect_scene_changes(file_path: str, threshold: float = 0.3) -> dict:
    """
    Detect scene cuts in a video file using FFprobe.
    threshold: 0.0-1.0, lower = more sensitive (detects more cuts).
    Returns a list of timestamps where scene changes occur.
    """
    import subprocess as sp
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_frames",
        "-of", "json",
        "-select_streams", "v:0",
        "-f", "lavfi",
        f"movie={file_path},select=gt(scene\\,{threshold})",
        "-show_entries", "frame=pkt_pts_time",
        file_path,
    ]
    # Simpler ffmpeg scene detect approach
    cmd2 = [
        "ffmpeg", "-i", file_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    try:
        result = sp.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "frame_tags=lavfi.scene_score",
                "-of", "json",
                "-select_streams", "v",
                "-f", "lavfi",
                f"movie={file_path},scdet=threshold={threshold}",
            ],
            capture_output=True, text=True, timeout=60
        )

        # Parse showinfo output for pts_time
        result2 = sp.run(
            ["ffmpeg", "-i", file_path, "-vf", f"scdet=threshold={threshold}", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120
        )

        scenes = []
        for line in result2.stderr.split("\n"):
            if "Parsed_scdet" in line and "pts_time" in line:
                try:
                    import re
                    m = re.search(r"pts_time:([\d.]+)", line)
                    if m:
                        scenes.append(round(float(m.group(1)), 2))
                except Exception:
                    pass

        return {
            "success": True,
            "file": file_path,
            "threshold": threshold,
            "scene_count": len(scenes),
            "scene_timestamps": scenes,
            "message": f"Found {len(scenes)} scene changes.",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_scene_cut_markers(file_path: str, threshold: float = 0.3) -> dict:
    """Detect scene changes in a file and add markers to the current timeline at each cut."""
    scene_result = detect_scene_changes(file_path, threshold)
    if not scene_result.get("success"):
        return scene_result

    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)

    added = 0
    for ts in scene_result["scene_timestamps"]:
        frame = int(ts * fps)
        ok = timeline.AddMarker(frame, "Cyan", "Scene Cut", f"at {ts:.2f}s", 1)
        if ok:
            added += 1

    return {
        "success": True,
        "markers_added": added,
        "scene_timestamps": scene_result["scene_timestamps"],
    }


# ─────────────────────────────────────────────
#  AI GENERATION + TIMELINE
# ─────────────────────────────────────────────

def generate_ai_image(
    prompt: str,
    provider: str = "auto",
    width: int = 1920,
    height: int = 1080,
    style: str = "cinematic",
) -> dict:
    """Generate an AI image using DALL-E 3 or Flux. Returns file path + preview."""
    from ai_generate import generate_image
    return generate_image(prompt, provider, width, height, style)


def drop_ai_image_to_timeline(
    file_path: str,
    position_seconds: float = -1,
    duration_seconds: float = 3.0,
) -> dict:
    """Add a generated AI image to the current Resolve timeline."""
    from ai_generate import add_image_to_timeline
    return add_image_to_timeline(file_path, position_seconds, duration_seconds)


def generate_ai_transition(
    clip_before_index: int = 0,
    clip_after_index: int = 1,
    transition_style: str = "cinematic blend",
    track: int = 1,
    duration_seconds: float = 2.0,
) -> dict:
    """
    Generate an AI transition frame between two clips and insert it onto the timeline.
    1. Grabs last frame of clip_before and first frame of clip_after.
    2. Generates an AI transition frame via DALL-E/Flux.
    3. Places it between the two clips.
    """
    from screen_capture import grab_resolve_frame
    from ai_generate import generate_transition_frame, add_image_to_timeline

    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []

    if clip_before_index >= len(clips):
        return {"error": f"Clip {clip_before_index} not found on track {track}"}
    if clip_after_index >= len(clips):
        return {"error": f"Clip {clip_after_index} not found on track {track}"}

    clip_before = clips[clip_before_index]
    clip_after = clips[clip_after_index]

    # Grab frame at end of clip_before
    timeline.SetCurrentTimecodeByFrame(clip_before.GetEnd() - 1)
    frame_a_result = grab_resolve_frame()

    # Grab frame at start of clip_after
    timeline.SetCurrentTimecodeByFrame(clip_after.GetStart())
    frame_b_result = grab_resolve_frame()

    # Generate transition
    import tempfile, base64, os
    frame_a_path, frame_b_path = None, None

    if "image_base64" in frame_a_result:
        frame_a_path = tempfile.mktemp(suffix=".jpg")
        with open(frame_a_path, "wb") as f:
            f.write(base64.b64decode(frame_a_result["image_base64"]))

    if "image_base64" in frame_b_result:
        frame_b_path = tempfile.mktemp(suffix=".jpg")
        with open(frame_b_path, "wb") as f:
            f.write(base64.b64decode(frame_b_result["image_base64"]))

    if not frame_a_path or not frame_b_path:
        # Fallback: generate without reference frames
        from ai_generate import generate_image
        result = generate_image(
            f"Cinematic {transition_style} transition frame for a video edit, professional production, high quality",
            style=transition_style,
        )
    else:
        result = generate_transition_frame(frame_a_path, frame_b_path, transition_style)

    # Cleanup temp frames
    for p in [frame_a_path, frame_b_path]:
        if p:
            try:
                os.unlink(p)
            except Exception:
                pass

    if not result.get("success"):
        return result

    # Insert between the two clips
    insert_pos = clip_before.GetEnd() / fps
    drop_result = add_image_to_timeline(result["file_path"], insert_pos, duration_seconds)

    return {
        "success": drop_result.get("success", False),
        "transition_file": result["file_path"],
        "image_base64": result.get("image_base64"),
        "media_type": result.get("media_type", "image/png"),
        "inserted_at": insert_pos,
        "duration": duration_seconds,
        "style": transition_style,
        "message": f"AI transition generated and inserted at {insert_pos:.2f}s",
    }


# ─────────────────────────────────────────────
#  AUTO COLOR TOOLS
# ─────────────────────────────────────────────

def auto_color(track: int = 1, clip_index: int = 0) -> dict:
    """Apply Resolve's automatic color balance to a clip."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    resolve.OpenPage("color")
    try:
        ok = clip.AutoBalance()
        return {"success": bool(ok), "clip": clip.GetName()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def match_color_to_clip(
    source_track: int = 1,
    source_clip_index: int = 0,
    target_track: int = 1,
    target_clip_index: int = 1,
) -> dict:
    """Match the color of one clip to another using Resolve's color match feature."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()

    src_clips = timeline.GetItemListInTrack("video", source_track) or []
    tgt_clips = timeline.GetItemListInTrack("video", target_track) or []

    if source_clip_index >= len(src_clips):
        return {"error": "Source clip not found"}
    if target_clip_index >= len(tgt_clips):
        return {"error": "Target clip not found"}

    resolve.OpenPage("color")
    src = src_clips[source_clip_index]
    tgt = tgt_clips[target_clip_index]

    try:
        ok = tgt.ColorMatch(src)
        return {
            "success": bool(ok),
            "source": src.GetName(),
            "target": tgt.GetName(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────
#  REAL EDITOR TOOLS
# ─────────────────────────────────────────────

def trim_clip_start(track: int = 1, clip_index: int = 0, trim_seconds: float = 0.0) -> dict:
    """Trim the start (in-point) of a clip by trim_seconds. Positive = trim inward, negative = extend."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    frames = int(trim_seconds * fps)
    try:
        ok = clip.TrimLeft(frames)
        return {"success": bool(ok), "clip": clip.GetName(), "trimmed_seconds": trim_seconds}
    except Exception:
        # Fallback: set left offset
        try:
            current = clip.GetLeftOffset()
            clip.SetLeftOffset(current + frames)
            return {"success": True, "clip": clip.GetName(), "trimmed_seconds": trim_seconds}
        except Exception as e:
            return {"success": False, "error": str(e)}


def trim_clip_end(track: int = 1, clip_index: int = 0, trim_seconds: float = 0.0) -> dict:
    """Trim the end (out-point) of a clip by trim_seconds. Positive = trim inward, negative = extend."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    frames = int(trim_seconds * fps)
    try:
        ok = clip.TrimRight(frames)
        return {"success": bool(ok), "clip": clip.GetName(), "trimmed_seconds": trim_seconds}
    except Exception:
        try:
            current = clip.GetRightOffset()
            clip.SetRightOffset(current + frames)
            return {"success": True, "clip": clip.GetName(), "trimmed_seconds": trim_seconds}
        except Exception as e:
            return {"success": False, "error": str(e)}


def ripple_delete_clip(track: int = 1, clip_index: int = 0) -> dict:
    """Delete a clip and close the gap (ripple delete)."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    name = clip.GetName()
    start = clip.GetStart()
    end = clip.GetEnd()
    fps = _fps(timeline)
    try:
        ok = timeline.DeleteClips([clip], True)  # True = ripple
        return {"success": bool(ok), "deleted": name, "start": start/fps, "end": end/fps}
    except Exception:
        ok = timeline.DeleteClips([clip])
        return {"success": bool(ok), "deleted": name, "note": "Deleted without ripple"}


def move_clip_to_position(track: int = 1, clip_index: int = 0, new_start_seconds: float = 0.0) -> dict:
    """Move a clip to a new start position on the timeline."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    new_frame = int(new_start_seconds * fps) + timeline.GetStartFrame()
    try:
        ok = clip.SetStart(new_frame)
        return {"success": bool(ok), "clip": clip.GetName(), "new_start": new_start_seconds}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cut_clips_at_beats(beat_times: list, track: int = 1) -> dict:
    """Place razor cuts at all beat timestamps. Provide beat_times as list of seconds."""
    results = []
    for t in beat_times:
        r = split_clip_at(t, track)
        results.append({"time": t, "success": r.get("success", False)})
    cuts_made = sum(1 for r in results if r["success"])
    return {
        "success": True,
        "cuts_made": cuts_made,
        "total_beats": len(beat_times),
        "results": results,
    }


def auto_rough_cut(track: int = 1, target_duration_seconds: float = 3.0) -> dict:
    """Trim all clips on a track to a target duration (rough cut pass)."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []
    trimmed = []
    for clip in clips:
        dur = clip.GetDuration() / fps
        if dur > target_duration_seconds:
            excess = dur - target_duration_seconds
            try:
                clip.SetRightOffset(clip.GetRightOffset() + int(excess * fps))
                trimmed.append({"clip": clip.GetName(), "original_duration": dur, "new_duration": target_duration_seconds})
            except Exception:
                pass
    return {"success": True, "trimmed": len(trimmed), "target_duration": target_duration_seconds, "clips": trimmed}


def reorder_clips(track: int = 1, new_order: list = None) -> dict:
    """Reorder clips on a track by providing a list of clip names in desired order."""
    if not new_order:
        return {"error": "new_order list is required"}
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []
    clip_map = {c.GetName(): c for c in clips}
    # Get durations sorted by desired order
    cursor = timeline.GetStartFrame()
    moved = []
    for name in new_order:
        if name in clip_map:
            clip = clip_map[name]
            dur = clip.GetDuration()
            try:
                clip.SetStart(cursor)
                moved.append(name)
                cursor += dur
            except Exception:
                pass
    return {"success": True, "reordered": moved}


def add_beats_as_markers(beat_times: list, color: str = "Yellow") -> dict:
    """Add timeline markers at every beat position."""
    results = []
    for i, t in enumerate(beat_times):
        r = add_marker(t, color, f"Beat {i+1}", "")
        results.append({"beat": i+1, "time": t, "success": r.get("success", False)})
    return {"success": True, "markers_added": sum(1 for r in results if r["success"]), "total": len(beat_times)}


def set_jl_cut(track: int = 1, clip_index: int = 0, audio_lead_seconds: float = 0.5) -> dict:
    """Create a J-cut: audio from next clip starts before the video cut."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    audio_clips = timeline.GetItemListInTrack("audio", track) or []
    video_clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index + 1 >= len(audio_clips):
        return {"error": "No next audio clip found"}
    next_audio = audio_clips[clip_index + 1]
    frames = int(audio_lead_seconds * fps)
    try:
        current_offset = next_audio.GetLeftOffset()
        next_audio.SetLeftOffset(max(0, current_offset - frames))
        return {"success": True, "audio_lead_seconds": audio_lead_seconds, "type": "J-cut"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def normalize_clip_audio(track: int = 1, clip_index: int = 0, target_db: float = -12.0) -> dict:
    """Set a clip's audio level to a target dB value."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    if clip_index >= len(clips):
        return {"error": "Clip not found"}
    clip = clips[clip_index]
    try:
        # Volume is in dB — convert to linear for Resolve's Volume property
        import math
        linear = 10 ** (target_db / 20.0)
        clip.SetProperty("Volume", linear)
        return {"success": True, "clip": clip.GetName(), "target_db": target_db, "linear": linear}
    except Exception as e:
        return {"success": False, "error": str(e)}


def apply_cross_dissolve_all(track: int = 1, duration_seconds: float = 0.5) -> dict:
    """Apply cross dissolve transitions between all clips on a track."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []
    added = 0
    for i in range(len(clips) - 1):
        clip = clips[i]
        cut_point = clip.GetEnd() / fps
        r = add_transition(cut_point, "Cross Dissolve", duration_seconds, track)
        if r.get("success"):
            added += 1
    return {"success": True, "transitions_added": added, "total_cuts": len(clips) - 1}


def detect_and_cut_silence(track: int = 1, min_silence_db: float = -50.0, min_duration_seconds: float = 0.5) -> dict:
    """
    Scan audio on track and mark silent regions. Returns timestamps of silence for review.
    Note: actual silence cutting requires the Fairlight API or manual review of markers.
    """
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("audio", track) or []
    # Flag clips that are very short (likely silence/dead air)
    flagged = []
    for clip in clips:
        dur = clip.GetDuration() / fps
        if dur < min_duration_seconds:
            flagged.append({"name": clip.GetName(), "start": clip.GetStart()/fps, "duration": dur})
            add_marker(clip.GetStart()/fps, "Red", "Silence", f"Short clip {dur:.2f}s")
    return {
        "success": True,
        "flagged_clips": len(flagged),
        "clips": flagged,
        "note": "Red markers added at silent/short clips for review",
    }


def color_grade_all_clips(track: int = 1, contrast: float = 1.05, saturation: float = 0.95,
                           lift_r: float = 0.0, lift_g: float = 0.0, lift_b: float = 0.02,
                           gain_r: float = 0.01, gain_g: float = 0.0, gain_b: float = -0.01) -> dict:
    """Apply a consistent color grade to ALL clips on a track — great for a whole-timeline look."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    clips = timeline.GetItemListInTrack("video", track) or []
    graded = 0
    for i, clip in enumerate(clips):
        try:
            set_contrast_saturation(contrast, saturation, track, i)
            apply_color_wheel("lift", lift_r, lift_g, lift_b, 0.0, track, i)
            apply_color_wheel("gain", gain_r, gain_g, gain_b, 0.0, track, i)
            graded += 1
        except Exception:
            pass
    return {"success": True, "clips_graded": graded, "total": len(clips)}


def create_multicam_cut(clips_per_second: float = 1.0, track: int = 1) -> dict:
    """Create rapid multicam-style cuts by splitting every clip into equal segments."""
    resolve = _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    fps = _fps(timeline)
    clips = timeline.GetItemListInTrack("video", track) or []
    segment_duration = 1.0 / clips_per_second
    cuts_made = 0
    for clip in clips:
        start = clip.GetStart() / fps
        end = clip.GetEnd() / fps
        t = start + segment_duration
        while t < end - 0.1:
            r = split_clip_at(t, track)
            if r.get("success"):
                cuts_made += 1
            t += segment_duration
    return {"success": True, "cuts_made": cuts_made, "segment_duration": segment_duration}
