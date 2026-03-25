"""
Screen capture utilities.
Takes screenshots of DaVinci Resolve (or full screen) and returns base64 images
for Claude's vision to analyze.
"""
import os
import subprocess
import tempfile
import base64
from typing import Optional


def _to_base64_jpeg(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def capture_screen(window_only: bool = False) -> dict:
    """
    Take a screenshot of the current screen.
    On macOS, tries to capture just the DaVinci Resolve window first,
    falls back to full screen.
    Returns base64-encoded JPEG for Claude vision.
    """
    tmp = tempfile.mktemp(suffix=".jpg")
    try:
        if window_only:
            # Try to get Resolve window ID via AppleScript
            try:
                script = (
                    'tell application "System Events" to '
                    'get unix id of (processes where name is "DaVinci Resolve")'
                )
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True, text=True, timeout=3
                )
                pid = result.stdout.strip()
                if pid:
                    # Use window capture by pid via screencapture
                    subprocess.run(
                        ["screencapture", "-x", "-t", "jpg", "-p", pid, tmp],
                        capture_output=True, timeout=5
                    )
            except Exception:
                pass

        # Fallback / default: full screen
        if not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            subprocess.run(
                ["screencapture", "-x", "-t", "jpg", tmp],
                capture_output=True, timeout=5
            )

        if not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            return {"error": "screencapture failed. Make sure you granted screen recording permission."}

        data = _to_base64_jpeg(tmp)
        size = os.path.getsize(tmp)
        return {
            "image_base64": data,
            "media_type": "image/jpeg",
            "size_bytes": size,
            "message": "Screenshot captured. I can now see your screen.",
        }
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def grab_resolve_frame() -> dict:
    """
    Export the current Resolve timeline frame as an image by:
    1. Using Resolve's GrabStill() API
    2. Falling back to screencapture if needed
    """
    try:
        import sys
        import os as _os
        _RESOLVE_API = _os.environ.get(
            "RESOLVE_SCRIPT_API",
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
        )
        sys.path.insert(0, _os.path.join(_RESOLVE_API, "Modules"))
        import DaVinciResolveScript as dvr

        resolve = dvr.scriptapp("Resolve")
        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline()

        if not timeline:
            return capture_screen()

        # Grab still to gallery
        still = timeline.GrabStill()
        if not still:
            return capture_screen()

        # Export still to temp dir
        export_dir = tempfile.mkdtemp()
        gallery = project.GetGallery()
        ok = gallery.ExportStills([still], export_dir, "frame", "jpg")

        if ok:
            # Find the exported file
            for fname in os.listdir(export_dir):
                if fname.endswith(".jpg") or fname.endswith(".png"):
                    fpath = os.path.join(export_dir, fname)
                    data = _to_base64_jpeg(fpath)
                    # Cleanup
                    import shutil
                    shutil.rmtree(export_dir, ignore_errors=True)
                    return {
                        "image_base64": data,
                        "media_type": "image/jpeg",
                        "message": "Current Resolve frame captured.",
                    }

    except Exception as e:
        pass

    # Final fallback
    return capture_screen()


def load_image_as_base64(path_or_url: str) -> dict:
    """
    Load an image from a local path or URL, return as base64.
    Used for reference color matching.
    """
    import urllib.request

    tmp = None
    try:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            tmp = tempfile.mktemp(suffix=".jpg")
            urllib.request.urlretrieve(path_or_url, tmp)
            path = tmp
        else:
            path = path_or_url

        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        # Detect media type
        ext = os.path.splitext(path)[1].lower()
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/jpeg")

        data = _to_base64_jpeg(path) if ext in (".jpg", ".jpeg") else base64.b64encode(
            open(path, "rb").read()
        ).decode()

        return {
            "image_base64": data,
            "media_type": media_type,
            "path": path,
        }
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass
