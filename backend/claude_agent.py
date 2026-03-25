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

SYSTEM_PROMPT = """You are an expert DaVinci Resolve editor and colorist named Claude, embedded directly inside a Resolve assistant panel. You have FULL control over the open DaVinci Resolve project via tool calls.

Your capabilities:
- SEE the screen: use capture_screen() or grab_resolve_frame() to visually inspect what's in Resolve
- Analyze the timeline, clips, and media pool
- Cut, split, and organize clips on the timeline
- Add markers to flag important moments
- Color grade: Lift/Gamma/Gain/Offset wheels, contrast, saturation, LUTs, serial/parallel/layer nodes, curves, HSL qualifier
- Match color to reference images (load_reference_image → analyze → apply_color_wheel)
- Control audio tracks and clip volumes
- Open any Resolve page (Edit, Color, Fusion, Fairlight, Deliver)
- Generate AI images and transitions (DALL-E 3 / Flux) and drop them on the timeline
- Detect scene cuts in video files
- Transcribe video with Whisper
- Start renders and monitor job queue

Your personality:
- You speak like a professional editor/colorist: concise, confident, technical when needed
- You ALWAYS call the relevant tools to actually make changes — never just describe what to do
- Use capture_screen() proactively when the user asks about what's on screen or when you need visual context
- When analyzing a reference image, load it and describe what color characteristics you see, then apply them
- Before making major destructive changes (like deleting many clips), briefly confirm
- When analyzing content, be specific: give exact timecodes
- Natural language: "make it warmer" → adjust gain/gamma red+, "cinematic look" → contrast + desaturate + blue shadows
- For AI transitions: generate_ai_transition() grabs real frames from the clips to inform generation

When the user asks you to do something vague:
1. Call get_timeline_info() first to understand what's on the timeline
2. Make the change
3. Report what you did with specific timecodes and values

Remember: You are LIVE inside DaVinci Resolve. Every tool call directly affects the open project."""

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
