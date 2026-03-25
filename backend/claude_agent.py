"""
Claude agent with DaVinci Resolve tool_use + vision support.
Handles streaming, tool execution, image tool results, and multi-turn conversations.
"""
import json
import asyncio
from typing import AsyncIterator, Optional
import anthropic

from tools.claude_tools import RESOLVE_TOOLS
import resolve_bridge as rb
import beat_detect as bd

SYSTEM_PROMPT = """You are a professional video editor and colorist named Claude, embedded live inside DaVinci Resolve. You have FULL control over the open project and think like a real editor — not just a tool executor.

## Your editing skills:

**Cutting & Structure**
- Analyze timeline, read clip names/durations, identify pacing problems
- Split clips, trim in/out points, ripple delete, reorder clips
- Cut to beat: detect_beats(music_file) → cut_clips_at_beats(beat_times) for music-synced edits
- Auto rough cut: trim all clips to target duration in one pass
- Multicam-style rapid cuts for music videos
- J-cuts and L-cuts for smooth audio transitions
- Flag and remove dead air / silence

**Color & Grade**
- Read current grade, apply wheels (lift/gamma/gain/offset), contrast, saturation
- Match grade to a reference image (load_reference_image → analyze → apply)
- Grade all clips at once with color_grade_all_clips()
- Create serial/parallel/layer nodes, curves, HSL qualifier
- Apply LUTs

**Audio**
- Set track and clip levels, normalize to broadcast standards (-12 dB dialogue, -18 dB music)
- Mute/unmute tracks, J-cuts for smoother transitions

**AI & Generation**
- Generate images with DALL-E 3 / Flux and drop to timeline
- Generate AI transitions using actual frames from your clips

**Transcription & Analysis**
- Transcribe clips with Whisper, add word-level markers
- Detect scene changes in files

**Render**
- Start, monitor, cancel renders

## How you work:
- ALWAYS use tools to make actual changes — never just describe what to do
- Start complex requests with get_timeline_info() to understand what you're working with
- Think like an editor: consider pacing, story, emotion — not just mechanical operations
- When the user says "cut to beat", ask for the music file path then detect_beats → cut_clips_at_beats
- When the user says "rough cut", auto_rough_cut() then review with them
- When the user says "make it cinematic", grade all clips + add cross dissolves + maybe slow motion on key clips
- Give specific feedback: timecodes, clip names, what changed
- Capture screen when you need visual context
- Before mass-destructive operations, briefly confirm

## Edit style vocabulary:
- "music video edit" → detect_beats + cut_clips_at_beats + create_multicam_cut
- "montage" → auto_rough_cut(2s) + cross_dissolves + cinematic grade
- "clean up" → detect_and_cut_silence + ripple_delete short clips
- "color pass" → color_grade_all_clips with appropriate look
- "rough cut" → auto_rough_cut + add markers for review points
- "sync to music" → detect_beats(music_path) → cut at every beat or every 2/4 beats

You are LIVE in Resolve. Every tool call directly modifies the open project."""

TOOL_HANDLERS = {
    # Project / navigation
    "get_project_info": lambda args: rb.get_project_info(),
    "get_timeline_info": lambda args: rb.get_timeline_info(),
    "list_timelines": lambda args: rb.list_timelines(),
    "switch_timeline": lambda args: rb.switch_timeline(**args),
    "switch_page": lambda args: rb.switch_page(**args),
    # Timeline / editing
    "add_marker": lambda args: rb.add_marker(**args),
    "delete_marker": lambda args: rb.delete_marker(**args),
    "set_playhead": lambda args: rb.set_playhead(**args),
    "split_clip_at": lambda args: rb.split_clip_at(**args),
    "delete_clips_in_range": lambda args: rb.delete_clips_in_range(**args),
    "set_clip_color": lambda args: rb.set_clip_color(**args),
    "add_clip_to_timeline": lambda args: rb.add_clip_to_timeline(**args),
    "get_media_pool_clips": lambda args: rb.get_media_pool_clips(),
    "add_transition": lambda args: rb.add_transition(**args),
    "set_clip_speed": lambda args: rb.set_clip_speed(**args),
    "flag_clip": lambda args: rb.flag_clip(**args),
    "unflag_clip": lambda args: rb.unflag_clip(**args),
    # Color grading
    "get_clip_grade": lambda args: rb.get_clip_grade(**args),
    "apply_color_wheel": lambda args: rb.apply_color_wheel(**args),
    "set_contrast_saturation": lambda args: rb.set_contrast_saturation(**args),
    "apply_lut": lambda args: rb.apply_lut(**args),
    "add_serial_node": lambda args: rb.add_serial_node(**args),
    "reset_grade": lambda args: rb.reset_grade(**args),
    "copy_grade_to_clips": lambda args: rb.copy_grade_to_clips(**args),
    "get_node_graph": lambda args: rb.get_node_graph(**args),
    "create_parallel_node": lambda args: rb.create_parallel_node(**args),
    "create_layer_node": lambda args: rb.create_layer_node(**args),
    "set_node_curves": lambda args: rb.set_node_curves(**args),
    "apply_hsl_qualifier": lambda args: rb.apply_hsl_qualifier(**args),
    "auto_color": lambda args: rb.auto_color(**args),
    "match_color_to_clip": lambda args: rb.match_color_to_clip(**args),
    # Audio
    "set_audio_track_volume": lambda args: rb.set_audio_track_volume(**args),
    "mute_audio_track": lambda args: rb.mute_audio_track(**args),
    "set_clip_audio_volume": lambda args: rb.set_clip_audio_volume(**args),
    # Transcription
    "transcribe_clip_file": lambda args: rb.transcribe_clip_file(**args),
    "apply_transcript_markers": lambda args: rb.apply_transcript_markers(**args),
    # Scene detection
    "detect_scene_changes": lambda args: rb.detect_scene_changes(**args),
    "add_scene_cut_markers": lambda args: rb.add_scene_cut_markers(**args),
    # Screen capture / vision
    "capture_screen": lambda args: rb.capture_screen(),
    "grab_resolve_frame": lambda args: rb.grab_resolve_frame(),
    "load_reference_image": lambda args: rb.load_reference_image(**args),
    # AI generation
    "generate_ai_image": lambda args: rb.generate_ai_image(**args),
    "drop_ai_image_to_timeline": lambda args: rb.drop_ai_image_to_timeline(**args),
    "generate_ai_transition": lambda args: rb.generate_ai_transition(**args),
    # Render
    "get_render_presets": lambda args: rb.get_render_presets(),
    "get_render_status": lambda args: rb.get_render_status(),
    "start_render": lambda args: rb.start_render(**args),
    "cancel_render": lambda args: rb.cancel_render(),
    # Fusion
    "open_fusion_for_clip": lambda args: rb.open_fusion_for_clip(**args),
    # Beat detection & sync
    "detect_beats": lambda args: bd.detect_beats(**args),
    "cut_clips_at_beats": lambda args: rb.cut_clips_at_beats(**args),
    "add_beats_as_markers": lambda args: rb.add_beats_as_markers(**args),
    # Trimming & ripple
    "trim_clip_start": lambda args: rb.trim_clip_start(**args),
    "trim_clip_end": lambda args: rb.trim_clip_end(**args),
    "ripple_delete_clip": lambda args: rb.ripple_delete_clip(**args),
    "move_clip_to_position": lambda args: rb.move_clip_to_position(**args),
    "reorder_clips": lambda args: rb.reorder_clips(**args),
    # Auto edit passes
    "auto_rough_cut": lambda args: rb.auto_rough_cut(**args),
    "create_multicam_cut": lambda args: rb.create_multicam_cut(**args),
    "apply_cross_dissolve_all": lambda args: rb.apply_cross_dissolve_all(**args),
    "detect_and_cut_silence": lambda args: rb.detect_and_cut_silence(**args),
    "color_grade_all_clips": lambda args: rb.color_grade_all_clips(**args),
    "normalize_clip_audio": lambda args: rb.normalize_clip_audio(**args),
    "set_jl_cut": lambda args: rb.set_jl_cut(**args),
}


# ─────────────────────────────────────────────
#  IMAGE-AWARE TOOL RESULT BUILDER
# ─────────────────────────────────────────────

def _build_tool_result_content(result_data: dict) -> list:
    """
    Build Anthropic content blocks for a tool result.
    If the result contains an image (image_base64), includes it as a vision block
    so Claude can actually SEE the image.
    """
    content = []

    if "image_base64" in result_data:
        # Add the image as a vision block
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": result_data.get("media_type", "image/jpeg"),
                "data": result_data["image_base64"],
            },
        })
        # Add remaining text metadata (strip the large base64)
        meta = {k: v for k, v in result_data.items() if k not in ("image_base64", "media_type")}
        if meta:
            content.append({"type": "text", "text": json.dumps(meta)})
    else:
        content.append({"type": "text", "text": json.dumps(result_data, indent=2)})

    return content


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a Resolve tool and return the raw result dict."""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return handler(tool_input)
    except Exception as e:
        return {"error": str(e)}


async def stream_chat(
    messages: list,
    model: str = "claude-sonnet-4-6",
    api_key: str = "",
) -> AsyncIterator[dict]:
    """
    Stream a chat response with tool_use + vision support.
    Yields SSE-style dicts: {type, content} or {type, tool_name, tool_input, tool_result}
    Image tool results are passed back to Claude as vision blocks (Claude can see them).
    """
    client = anthropic.Anthropic(api_key=api_key)
    current_messages = list(messages)

    while True:
        full_text = ""
        tool_calls = []
        stop_reason = None

        with client.messages.stream(
            model=model,
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            tools=RESOLVE_TOOLS,
            messages=current_messages,
        ) as stream:
            for event in stream:
                if not hasattr(event, "type"):
                    continue

                if event.type == "content_block_start":
                    if hasattr(event, "content_block") and event.content_block.type == "tool_use":
                        tool_calls.append({
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input_str": "",
                        })

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        full_text += delta.text
                        yield {"type": "text", "content": delta.text}
                    elif delta.type == "input_json_delta" and tool_calls:
                        tool_calls[-1]["input_str"] += delta.partial_json

                elif event.type == "message_delta":
                    stop_reason = getattr(event.delta, "stop_reason", None)

        if stop_reason != "tool_use" or not tool_calls:
            break

        # Build assistant message content
        assistant_content = []
        if full_text:
            assistant_content.append({"type": "text", "text": full_text})

        tool_results = []
        for tc in tool_calls:
            try:
                tool_input = json.loads(tc["input_str"]) if tc["input_str"] else {}
            except Exception:
                tool_input = {}

            # Yield tool call event to frontend
            yield {
                "type": "tool_call",
                "tool_name": tc["name"],
                "tool_input": tool_input,
            }

            # Execute tool
            result_data = await asyncio.to_thread(execute_tool, tc["name"], tool_input)

            # Yield result to frontend (strip large base64 from SSE)
            frontend_result = {k: v for k, v in result_data.items() if k != "image_base64"}
            if "image_base64" in result_data:
                frontend_result["has_image"] = True
            yield {
                "type": "tool_result",
                "tool_name": tc["name"],
                "result": frontend_result,
            }

            # Build content blocks (with image if present — Claude will SEE it)
            result_content = _build_tool_result_content(result_data)

            assistant_content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": tool_input,
            })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": result_content,
            })

        current_messages = current_messages + [
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": tool_results},
        ]

    yield {"type": "done"}
