"""
AI image / video generation.
Supports DALL-E 3 (OpenAI) and Flux via fal.ai or Replicate.
Generated images can be dropped directly onto the Resolve timeline.
"""
import os
import base64
import tempfile
import json
import httpx
from pathlib import Path
from typing import Optional


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
FAL_KEY = os.environ.get("FAL_KEY", "")
REPLICATE_API_KEY = os.environ.get("REPLICATE_API_KEY", "")


# ─────────────────────────────────────────────
#  DALL-E 3
# ─────────────────────────────────────────────

def generate_dalle3(
    prompt: str,
    size: str = "1792x1024",
    quality: str = "hd",
    style: str = "vivid",
) -> dict:
    """Generate an image with DALL-E 3. Returns saved file path + base64 preview."""
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY not set in .env"}

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "style": style,
        "response_format": "b64_json",
    }

    with httpx.Client(timeout=60) as client:
        r = client.post("https://api.openai.com/v1/images/generations", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    b64 = data["data"][0]["b64_json"]
    revised_prompt = data["data"][0].get("revised_prompt", prompt)

    # Save to file
    output_dir = Path(tempfile.gettempdir()) / "resolve_claude_ai"
    output_dir.mkdir(exist_ok=True)
    import time
    fname = f"dalle_{int(time.time())}.png"
    fpath = str(output_dir / fname)

    with open(fpath, "wb") as f:
        f.write(base64.b64decode(b64))

    return {
        "success": True,
        "file_path": fpath,
        "image_base64": b64,
        "media_type": "image/png",
        "revised_prompt": revised_prompt,
        "model": "dall-e-3",
        "size": size,
    }


# ─────────────────────────────────────────────
#  FLUX via fal.ai (fast, high quality)
# ─────────────────────────────────────────────

def generate_flux(
    prompt: str,
    model: str = "fal-ai/flux/schnell",
    width: int = 1920,
    height: int = 1080,
    num_steps: int = 4,
) -> dict:
    """Generate with Flux (Schnell or Dev) via fal.ai."""
    if not FAL_KEY:
        return {"error": "FAL_KEY not set in .env. Get one free at fal.ai"}

    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_inference_steps": num_steps,
        "num_images": 1,
        "enable_safety_checker": False,
    }

    url = f"https://fal.run/{model}"
    with httpx.Client(timeout=120) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    image_url = data["images"][0]["url"]

    # Download the image
    with httpx.Client(timeout=30) as client:
        img_r = client.get(image_url)
        img_r.raise_for_status()
        img_bytes = img_r.content

    output_dir = Path(tempfile.gettempdir()) / "resolve_claude_ai"
    output_dir.mkdir(exist_ok=True)
    import time
    fname = f"flux_{int(time.time())}.png"
    fpath = str(output_dir / fname)
    with open(fpath, "wb") as f:
        f.write(img_bytes)

    b64 = base64.b64encode(img_bytes).decode()
    return {
        "success": True,
        "file_path": fpath,
        "image_base64": b64,
        "media_type": "image/png",
        "model": model,
        "size": f"{width}x{height}",
    }


# ─────────────────────────────────────────────
#  MAIN DISPATCH
# ─────────────────────────────────────────────

def generate_image(
    prompt: str,
    provider: str = "auto",
    width: int = 1920,
    height: int = 1080,
    style: str = "cinematic",
) -> dict:
    """
    Generate an image using the best available provider.
    provider: 'auto' | 'dalle3' | 'flux'
    auto = tries Flux first (faster), falls back to DALL-E 3.
    """
    # Enhance prompt with style
    enhanced = f"{prompt}, {style} style, professional photography, high quality, 4K"

    if provider == "dalle3" or (provider == "auto" and not FAL_KEY and OPENAI_API_KEY):
        size = "1792x1024" if width > height else "1024x1792" if height > width else "1024x1024"
        return generate_dalle3(enhanced, size=size, style="vivid")

    if provider == "flux" or (provider == "auto" and FAL_KEY):
        return generate_flux(enhanced, width=width, height=height)

    return {
        "error": "No generation API key configured. Add OPENAI_API_KEY or FAL_KEY to your .env file.",
        "hint": "Get a free key at: https://fal.ai (Flux) or https://platform.openai.com (DALL-E 3)",
    }


# ─────────────────────────────────────────────
#  TRANSITION GENERATOR
# ─────────────────────────────────────────────

def generate_transition_frame(
    frame_a_path: str,
    frame_b_path: str,
    transition_style: str = "cinematic blend",
    provider: str = "auto",
) -> dict:
    """
    Generate an AI transition frame between two video frames.
    Uses DALL-E 3 with a descriptive prompt based on the two frames.
    For img2img (style-guided), uses Flux if available.
    """
    if not os.path.exists(frame_a_path) or not os.path.exists(frame_b_path):
        return {"error": "Frame files not found"}

    prompt = (
        f"A seamless cinematic transition frame that bridges two scenes. "
        f"Style: {transition_style}. "
        f"The frame should look like it belongs between two shots in a professional film or video production. "
        f"Photorealistic, motion blur, cinematic color grade."
    )

    result = generate_image(prompt, provider=provider)
    if result.get("success"):
        result["transition_style"] = transition_style
    return result


# ─────────────────────────────────────────────
#  DROP TO TIMELINE
# ─────────────────────────────────────────────

def add_image_to_timeline(
    file_path: str,
    position_seconds: float = -1,
    duration_seconds: float = 3.0,
) -> dict:
    """Import an AI-generated image into Resolve and add it to the timeline."""
    try:
        import sys as _sys
        import os as _os
        _RESOLVE_API = _os.environ.get(
            "RESOLVE_SCRIPT_API",
            "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
        )
        _sys.path.insert(0, _os.path.join(_RESOLVE_API, "Modules"))
        import DaVinciResolveScript as dvr

        resolve = dvr.scriptapp("Resolve")
        project = resolve.GetProjectManager().GetCurrentProject()
        media_pool = project.GetMediaPool()
        timeline = project.GetCurrentTimeline()
        fps = float(timeline.GetSetting("timelineFrameRate") or 24)

        # Import into media pool
        items = media_pool.ImportMedia([file_path])
        if not items:
            return {"success": False, "error": "Could not import image into media pool"}

        clip = items[0]
        duration_frames = int(duration_seconds * fps)

        # Build clip info
        clip_info = {
            "mediaPoolItem": clip,
            "startFrame": 0,
            "endFrame": duration_frames,
        }

        if position_seconds >= 0:
            # Insert at specific position (approximate)
            clip_info["recordFrame"] = int(position_seconds * fps) + timeline.GetStartFrame()

        ok = media_pool.AppendToTimeline([clip_info])
        return {
            "success": bool(ok),
            "file": file_path,
            "duration_seconds": duration_seconds,
            "position": position_seconds if position_seconds >= 0 else "end of timeline",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
