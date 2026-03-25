"""
Claude agent with DaVinci Resolve tool_use.
Handles streaming, tool execution, and multi-turn conversations.
"""
import json
import asyncio
from typing import AsyncIterator, Optional
import anthropic

from tools.claude_tools import RESOLVE_TOOLS
import resolve_bridge as rb

SYSTEM_PROMPT = """You are an expert DaVinci Resolve editor and colorist named Claude, embedded directly inside a Resolve assistant panel. You have FULL control over the open DaVinci Resolve project via tool calls.

Your capabilities:
- Analyze the timeline, clips, and media pool
- Cut, split, and organize clips on the timeline
- Add markers to flag important moments
- Color grade clips (Lift/Gamma/Gain/Offset wheels, contrast, saturation, LUTs, nodes)
- Control audio tracks and clip volumes
- Open any Resolve page (Edit, Color, Fusion, Fairlight, Deliver)
- Add clips to the timeline from the media pool
- Start renders

Your personality:
- You speak like a professional editor/colorist: concise, confident, technical when needed
- You ALWAYS call the relevant tools to actually make changes — never just describe what to do
- Before making major destructive changes (like deleting many clips), briefly confirm what you're about to do
- When analyzing content, be specific: give exact timecodes
- You can handle natural language like "make it warmer", "cut the boring parts", "add a marker at the best moment"

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
    # Audio
    "set_audio_track_volume": lambda args: rb.set_audio_track_volume(**args),
    "mute_audio_track": lambda args: rb.mute_audio_track(**args),
    "set_clip_audio_volume": lambda args: rb.set_clip_audio_volume(**args),
    # Transcription
    "transcribe_clip_file": lambda args: rb.transcribe_clip_file(**args),
    "apply_transcript_markers": lambda args: rb.apply_transcript_markers(**args),
    # Render
    "get_render_presets": lambda args: rb.get_render_presets(),
    "get_render_status": lambda args: rb.get_render_status(),
    "start_render": lambda args: rb.start_render(**args),
    "cancel_render": lambda args: rb.cancel_render(),
    # Fusion
    "open_fusion_for_clip": lambda args: rb.open_fusion_for_clip(**args),
}


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a Resolve tool and return the result as a JSON string."""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = handler(tool_input)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def stream_chat(
    messages: list,
    model: str = "claude-sonnet-4-6",
    api_key: str = "",
) -> AsyncIterator[dict]:
    """
    Stream a chat response with tool_use support.
    Yields SSE-style dicts: {type, content} or {type, tool_name, tool_input, tool_result}
    """
    client = anthropic.Anthropic(api_key=api_key)

    current_messages = list(messages)

    while True:
        # Collect full streaming response
        full_text = ""
        tool_calls = []
        stop_reason = None

        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=RESOLVE_TOOLS,
            messages=current_messages,
        ) as stream:
            for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_start":
                        if hasattr(event, "content_block"):
                            if event.content_block.type == "tool_use":
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
                        elif delta.type == "input_json_delta":
                            if tool_calls:
                                tool_calls[-1]["input_str"] += delta.partial_json

                    elif event.type == "message_delta":
                        stop_reason = getattr(event.delta, "stop_reason", None)

        # If no tool calls, we're done
        if stop_reason != "tool_use" or not tool_calls:
            break

        # Parse tool inputs and execute
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

            # Execute in Resolve
            result_str = await asyncio.to_thread(execute_tool, tc["name"], tool_input)
            result_data = json.loads(result_str)

            # Yield tool result event
            yield {
                "type": "tool_result",
                "tool_name": tc["name"],
                "result": result_data,
            }

            assistant_content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["name"],
                "input": tool_input,
            })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": result_str,
            })

        # Add assistant message + tool results and continue loop
        current_messages = current_messages + [
            {"role": "assistant", "content": assistant_content},
            {"role": "user", "content": tool_results},
        ]

    yield {"type": "done"}
