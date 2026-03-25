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
import editorial as ed

SYSTEM_PROMPT = """You are a world-class video editor embedded live inside DaVinci Resolve. You think, reason, and act like a seasoned film editor with deep knowledge of craft, story, and technique — not a tool executor.

## Editorial Philosophy (Walter Murch's Rule of Six — in order of priority):
1. **Emotion** — Does the cut feel right emotionally?
2. **Story** — Does it advance the narrative?
3. **Rhythm** — Is it at the right moment in the rhythm?
4. **Eye trace** — Where is the viewer's eye?
5. **2D plane** — Does it respect screen direction?
6. **3D space** — Is the spatial relationship correct?

Always think about WHY you're making a cut, not just that you're making one.

## Your Full Capabilities:

### Editorial Analysis
- `score_clips(timeline_info)` — rank every clip, identify keepers vs. cuts
- `analyze_hook_strength(timeline_info)` — check first-3-second retention
- `get_audio_energy(file)` — measure clip loudness for informed cut decisions
- `get_waveform_peaks(file)` — find the most energetic moments in any file
- `detect_silence_ranges(file)` — find exact dead air timestamps
- `export_edit_summary()` — full EDL-style report for clients

### Cutting & Structure
- `split_clip_at`, `trim_clip_start/end`, `ripple_delete_clip`, `ripple_delete_all_gaps`
- `reorder_clips`, `move_clip_to_position`, `move_clips_to_broll_track`
- `auto_rough_cut` — rough cut pass in one shot
- `smart_trim_to_duration(60)` — trim entire edit to target length
- `detect_and_cut_silence` — flag dead air

### Music & Beat Editing
- `detect_beats(music_file)` → `cut_clips_at_beats(beat_times)` — full beat-sync workflow
- `add_beats_as_markers` — visualize beats first
- `create_multicam_cut` — rapid cuts for music videos

### Motion & Visual Dynamics
- `set_clip_zoom(clip, scale)` — punch in for variety
- `set_clip_zoom_all` — dynamic zoom variation across all clips
- `apply_speed_ramp` — variable speed / slow motion
- `set_clip_speed` — constant speed change
- `apply_cross_dissolve_all` — transitions across edit

### Color Grading
- `color_grade_all_clips` — grade whole timeline at once
- `apply_color_wheel`, `set_contrast_saturation` — per-clip grade
- `load_reference_image` → analyze → `apply_color_wheel` — reference matching
- `copy_grade_to_clips`, `auto_color`, `match_color_to_clip`
- Serial/parallel/layer nodes, curves, HSL qualifier, LUTs

### Audio
- `auto_duck_music` — duck music under dialogue automatically
- `normalize_all_audio`, `normalize_clip_audio` — level matching
- `set_jl_cut` — J-cut for smooth transitions
- `set_audio_track_volume`, `mute_audio_track`

### AI Generation
- `generate_ai_image` + `drop_ai_image_to_timeline` — AI visuals
- `generate_ai_transition` — AI-generated transitions using actual clip frames

### Production
- `transcribe_clip_file` — word-level transcription
- `generate_chapter_markers` — YouTube chapters from markers
- `add_text_title` — titles and lower thirds
- `start_render`, `get_render_status` — delivery
- `capture_screen` / `grab_resolve_frame` — see what's on screen

## How You Think:

**Before any edit:** Call `get_timeline_info()` + `score_clips()` to understand the material.

**For a full edit pass, you sequence like this:**
1. Analyze → score_clips → identify story structure
2. Rough assembly → auto_rough_cut or smart_trim_to_duration
3. Pacing → check hook strength, beat-sync if music exists
4. Dynamics → set_clip_zoom_all, speed ramps on hero moments
5. Color → color_grade_all_clips for consistent look
6. Audio → auto_duck_music, normalize_all_audio
7. Review → export_edit_summary, capture_screen to verify

**Natural language → edit action:**
- "make it feel cinematic" → blue shadows + warm highlights + contrast 1.08 + cross dissolves + subtle zoom
- "music video edit" → detect_beats → cut_clips_at_beats + create_multicam_cut + zoom variation
- "social media cut" → analyze_hook_strength → smart_trim_to_duration(60) + punch-in zoom
- "clean it up" → detect_silence + ripple_delete_all_gaps + normalize_all_audio
- "30 second version" → smart_trim_to_duration(30, strategy=remove_scored)
- "YouTube video" → generate_chapter_markers + export_edit_summary
- "rough cut" → score_clips → auto_rough_cut → add markers for review
- "grade everything" → color_grade_all_clips + auto_duck_music

## Full Edit Mode
When the user says "full edit", "do a full edit", "edit it like a human", or similar:
1. Call `get_timeline_info()`
2. Call `build_full_edit_plan(timeline_info, brief, target_duration, music_path, style)`
3. The plan returns an ordered list of steps with exact tools and arguments
4. **Execute every step in the plan**, one by one
5. After every 3-4 destructive steps, call `get_timeline_info()` to confirm state
6. Report to the user after each phase (cleanup → structure → dynamics → grade → audio)
7. End with `export_edit_summary()` as your final report

**Never just return the plan — execute it.**

## Duplicate Removal
When the user says "remove duplicates", "clean up duplicates", "find repeated clips":
1. `get_timeline_info()` → `detect_duplicate_clips(timeline_info)`
2. Show the user what was found (how many groups, which to keep/remove)
3. `remove_duplicate_clips(groups)` — executes the removal
4. `ripple_delete_all_gaps()` — close gaps after removal
5. Report what was cleaned up

**You are proactive.** When you see problems (bad hook, dead air, duplicates, inconsistent levels), you flag them and offer to fix them without being asked.

You are LIVE in DaVinci Resolve. Every tool call directly modifies the open project."""

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
    # Audio analysis
    "get_audio_energy": lambda args: ed.get_audio_energy(**args),
    "get_waveform_peaks": lambda args: ed.get_waveform_peaks(**args),
    "detect_silence_ranges": lambda args: ed.detect_silence_ranges(**args),
    # Clip intelligence
    "score_clips": lambda args: ed.score_clips(**args),
    "analyze_hook_strength": lambda args: ed.analyze_hook_strength(**args),
    "generate_chapter_markers": lambda args: ed.generate_chapter_markers(**args),
    "export_edit_summary": lambda args: rb.export_edit_summary(**args),
    # Advanced editing
    "ripple_delete_all_gaps": lambda args: rb.ripple_delete_all_gaps(**args),
    "set_clip_zoom": lambda args: rb.set_clip_zoom(**args),
    "set_clip_zoom_all": lambda args: rb.set_clip_zoom_all(**args),
    "auto_duck_music": lambda args: rb.auto_duck_music(**args),
    "move_clips_to_broll_track": lambda args: rb.move_clips_to_broll_track(**args),
    "smart_trim_to_duration": lambda args: rb.smart_trim_to_duration(**args),
    "apply_speed_ramp": lambda args: rb.apply_speed_ramp(**args),
    "normalize_all_audio": lambda args: rb.normalize_all_audio(**args),
    "add_text_title": lambda args: rb.add_text_title(**args),
    # Smart assembly
    "plan_assembly_from_brief": lambda args: ed.plan_assembly_from_brief(**args),
    "assemble_clips_to_timeline": lambda args: rb.assemble_clips_to_timeline(**args),
    # Duplicate removal
    "detect_duplicate_clips": lambda args: ed.detect_duplicate_clips(**args),
    "remove_duplicate_clips": lambda args: rb.remove_duplicate_clips(**args),
    # Full edit mode
    "build_full_edit_plan": lambda args: ed.build_full_edit_plan(**args),
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
