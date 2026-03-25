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
        # Fallback: set out point of current clip then add cut
        ok = False

    return {"success": ok, "time": time_seconds, "track": track}


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
