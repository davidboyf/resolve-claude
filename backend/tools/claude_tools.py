"""
All Claude tool definitions — maps to resolve_bridge functions.
"""

RESOLVE_TOOLS = [
    # ── PROJECT / STATUS ──────────────────────────────────────────────
    {
        "name": "get_project_info",
        "description": "Get the current DaVinci Resolve project name, list of timelines, and available render presets.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_timeline_info",
        "description": "Get detailed information about the current timeline: all video/audio tracks, every clip with start/end times, duration, and all markers.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_timelines",
        "description": "List all timelines in the current project with their names and FPS.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "switch_timeline",
        "description": "Switch the active timeline to a different one by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Exact name of the timeline to switch to"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "switch_page",
        "description": "Switch DaVinci Resolve to a specific page/workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "string",
                    "description": "One of: media, cut, edit, fusion, color, fairlight, deliver",
                    "enum": ["media", "cut", "edit", "fusion", "color", "fairlight", "deliver"],
                }
            },
            "required": ["page"],
        },
    },
    # ── TIMELINE / EDITING ────────────────────────────────────────────
    {
        "name": "add_marker",
        "description": "Add a colored marker at a specific timestamp in the timeline. Great for flagging good takes, bad sections, chapter points, or anything to review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_seconds": {"type": "number", "description": "Timestamp in seconds"},
                "color": {
                    "type": "string",
                    "default": "Blue",
                    "description": "Marker color: Red, Green, Blue, Cyan, Magenta, Yellow, White",
                },
                "name": {"type": "string", "description": "Short label for the marker"},
                "note": {"type": "string", "description": "Longer description/note"},
            },
            "required": ["time_seconds"],
        },
    },
    {
        "name": "delete_marker",
        "description": "Remove a marker at a specific timestamp.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_seconds": {"type": "number"}
            },
            "required": ["time_seconds"],
        },
    },
    {
        "name": "set_playhead",
        "description": "Move the DaVinci Resolve playhead to a specific time so the user can see that moment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_seconds": {"type": "number"}
            },
            "required": ["time_seconds"],
        },
    },
    {
        "name": "split_clip_at",
        "description": "Split (razor cut) a video clip at a specific time on a track.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_seconds": {"type": "number"},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["time_seconds"],
        },
    },
    {
        "name": "delete_clips_in_range",
        "description": "Delete all video clips within a time range on a track. Use to remove dead air, bad takes, or unwanted sections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_seconds": {"type": "number"},
                "end_seconds": {"type": "number"},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["start_seconds", "end_seconds"],
        },
    },
    {
        "name": "set_clip_color",
        "description": "Set the label/flag color on a clip in the timeline for organization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_name": {"type": "string"},
                "color": {"type": "string", "description": "Orange, Apricot, Yellow, Lime, Green, Teal, Navy, Blue, Purple, Violet, Pink, Tan, Beige, Brown, Chocolate"},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["clip_name", "color"],
        },
    },
    {
        "name": "add_clip_to_timeline",
        "description": "Import a media file from disk and add it to the current timeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "media_path": {"type": "string"},
                "start_seconds": {"type": "number", "default": 0},
                "end_seconds": {"type": "number"},
            },
            "required": ["media_path"],
        },
    },
    {
        "name": "get_media_pool_clips",
        "description": "List all clips currently in the DaVinci Resolve media pool with file paths, duration, and resolution.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_transition",
        "description": "Add a transition between two adjacent clips. Types: 'Cross Dissolve', 'Dip to Color Dissolve', 'Dip to Black'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_index": {"type": "integer", "description": "0-based index of the clip to add the transition to"},
                "transition_type": {"type": "string", "default": "Cross Dissolve", "description": "Cross Dissolve, Dip to Color Dissolve, Dip to Black"},
                "duration_frames": {"type": "integer", "default": 24, "description": "Length in frames"},
                "position": {"type": "string", "default": "end", "enum": ["start", "end", "both"]},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["clip_index"],
        },
    },
    {
        "name": "set_clip_speed",
        "description": "Set the playback speed of a video clip. 100=normal, 50=half speed, 200=double speed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_index": {"type": "integer"},
                "speed_percent": {"type": "number", "default": 100.0},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["clip_index", "speed_percent"],
        },
    },
    {
        "name": "flag_clip",
        "description": "Add a colored flag to a clip. flag_color: Red, Green, Blue, Cyan, Magenta, Yellow.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_index": {"type": "integer"},
                "flag_color": {"type": "string", "default": "Red"},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["clip_index"],
        },
    },
    {
        "name": "unflag_clip",
        "description": "Remove a flag from a clip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_index": {"type": "integer"},
                "flag_color": {"type": "string", "default": "Red"},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["clip_index"],
        },
    },
    # ── COLOR GRADING ─────────────────────────────────────────────────
    {
        "name": "get_clip_grade",
        "description": "Read the current color grade values for a clip: Lift/Gamma/Gain/Offset wheels, contrast, saturation. Call this before modifying a grade to understand the current state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "apply_color_wheel",
        "description": "Adjust the Lift, Gamma, Gain, or Offset color wheel on a clip. Values -1.0 to 1.0 (0 = no change). Lift=shadows, Gamma=mids, Gain=highlights, Offset=all.",
        "input_schema": {
            "type": "object",
            "properties": {
                "wheel": {"type": "string", "enum": ["lift", "gamma", "gain", "offset"]},
                "red": {"type": "number", "default": 0.0},
                "green": {"type": "number", "default": 0.0},
                "blue": {"type": "number", "default": 0.0},
                "luma": {"type": "number", "default": 0.0, "description": "Master luminance offset"},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": ["wheel"],
        },
    },
    {
        "name": "set_contrast_saturation",
        "description": "Set contrast (0.0-2.0, 1.0=normal) and saturation (0.0-2.0, 1.0=normal) on a clip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contrast": {"type": "number", "default": 1.0},
                "saturation": {"type": "number", "default": 1.0},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "apply_lut",
        "description": "Apply a .cube LUT file to a clip for a specific look or color transform.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lut_path": {"type": "string", "description": "Absolute path to .cube LUT file"},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": ["lut_path"],
        },
    },
    {
        "name": "add_serial_node",
        "description": "Add a new serial color correction node to a clip's node graph.",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "default": "New Node"},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "reset_grade",
        "description": "Reset all color grading on a clip back to defaults.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "copy_grade_to_clips",
        "description": "Copy the color grade from one clip to one or more other clips.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_track": {"type": "integer", "default": 1},
                "source_clip_index": {"type": "integer", "default": 0},
                "target_track": {"type": "integer", "default": 1},
                "target_clip_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of 0-based clip indices to copy the grade to",
                },
            },
            "required": ["target_clip_indices"],
        },
    },
    # ── AUDIO ─────────────────────────────────────────────────────────
    {
        "name": "set_audio_track_volume",
        "description": "Set the volume of an audio track in dB. 0=unity, -6=half, negative=quieter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer"},
                "volume_db": {"type": "number"},
            },
            "required": ["track", "volume_db"],
        },
    },
    {
        "name": "mute_audio_track",
        "description": "Mute or unmute an audio track.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer"},
                "muted": {"type": "boolean", "default": True},
            },
            "required": ["track"],
        },
    },
    {
        "name": "set_clip_audio_volume",
        "description": "Set volume on a specific audio clip by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_name": {"type": "string"},
                "volume_db": {"type": "number"},
                "audio_track": {"type": "integer", "default": 1},
            },
            "required": ["clip_name", "volume_db"],
        },
    },
    # ── TRANSCRIPTION ─────────────────────────────────────────────────
    {
        "name": "transcribe_clip_file",
        "description": "Transcribe a video or audio file using Whisper AI to get the full spoken text with timestamps. Use this to understand what's being said and decide where to cut.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to video or audio file"},
                "language": {"type": "string", "default": "en"},
                "model_size": {
                    "type": "string",
                    "default": "base",
                    "description": "tiny (fastest), base, small, medium, large (most accurate)",
                    "enum": ["tiny", "base", "small", "medium", "large"],
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "apply_transcript_markers",
        "description": "Transcribe a file and automatically add markers to the timeline. mode='silence' adds Red markers on silent gaps; mode='segments' adds Blue markers at each speech segment start.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "mode": {"type": "string", "default": "silence", "enum": ["silence", "segments"]},
                "language": {"type": "string", "default": "en"},
                "model_size": {"type": "string", "default": "base", "enum": ["tiny", "base", "small", "medium", "large"]},
            },
            "required": ["file_path"],
        },
    },
    # ── RENDER ────────────────────────────────────────────────────────
    {
        "name": "get_render_presets",
        "description": "List all available render presets in the current project.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_render_status",
        "description": "Get the current render job queue with status and completion percentage for each job.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "start_render",
        "description": "Start rendering the timeline to a file using a render preset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "preset_name": {"type": "string"},
                "output_path": {"type": "string", "description": "Absolute directory path for output"},
            },
            "required": ["preset_name", "output_path"],
        },
    },
    {
        "name": "cancel_render",
        "description": "Stop all in-progress render jobs.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # ── FUSION ────────────────────────────────────────────────────────
    {
        "name": "open_fusion_for_clip",
        "description": "Open the Fusion VFX page for a specific clip so the user can add effects nodes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    # ── SCREEN CAPTURE / VISUAL FEEDBACK ─────────────────────────────
    {
        "name": "capture_screen",
        "description": "Take a screenshot of the screen so you can SEE what's currently on DaVinci Resolve. Use this whenever you need to understand what's visible, what the user is looking at, or to visually verify changes.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "grab_resolve_frame",
        "description": "Export the current Resolve timeline frame as an image to visually analyze the video content, color grade, or composition at the current playhead position.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "load_reference_image",
        "description": "Load a reference image from a local file path or URL so you can analyze its color grade, lighting, and style to match it on a Resolve clip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path_or_url": {"type": "string", "description": "Absolute file path or https:// URL to the reference image"},
            },
            "required": ["path_or_url"],
        },
    },
    # ── ADVANCED COLOR NODES ──────────────────────────────────────────
    {
        "name": "get_node_graph",
        "description": "Get the color node graph structure for a clip — lists all nodes, their labels and types.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "create_parallel_node",
        "description": "Add a parallel color node to a clip's node graph. Parallel nodes let you blend multiple color corrections together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "default": "Parallel"},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "create_layer_node",
        "description": "Add a layer mixer node to a clip's node graph. Layer nodes combine multiple inputs with blend modes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "default": "Layer"},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "set_node_curves",
        "description": "Set custom curve control points on a color node. curve_type: 'custom' (RGB), 'lum_vs_lum', 'hue_vs_sat', 'hue_vs_hue', 'sat_vs_sat'. control_points: list of [input, output] pairs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_index": {"type": "integer", "default": 1},
                "curve_type": {"type": "string", "default": "custom", "enum": ["custom", "lum_vs_lum", "hue_vs_sat", "hue_vs_hue", "sat_vs_sat", "hue_vs_lum"]},
                "control_points": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
                    "description": "List of [input, output] pairs, e.g. [[0,0],[0.5,0.65],[1,1]]",
                },
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": ["control_points"],
        },
    },
    {
        "name": "apply_hsl_qualifier",
        "description": "Apply an HSL qualifier (secondary color correction) to isolate a specific color range. Great for fixing skin tones, sky, grass without affecting the rest of the image.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hue_center": {"type": "number", "description": "Center hue 0-360 (red=0, yellow=60, green=120, cyan=180, blue=240, magenta=300)"},
                "hue_width": {"type": "number", "default": 30.0, "description": "Width of hue selection in degrees"},
                "sat_min": {"type": "number", "default": 0.2},
                "sat_max": {"type": "number", "default": 1.0},
                "lum_min": {"type": "number", "default": 0.0},
                "lum_max": {"type": "number", "default": 1.0},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": ["hue_center"],
        },
    },
    {
        "name": "auto_color",
        "description": "Apply Resolve's automatic color balance to a clip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "match_color_to_clip",
        "description": "Match the color of a target clip to a source clip using Resolve's color match feature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_track": {"type": "integer", "default": 1},
                "source_clip_index": {"type": "integer", "default": 0},
                "target_track": {"type": "integer", "default": 1},
                "target_clip_index": {"type": "integer", "default": 1},
            },
            "required": [],
        },
    },
    # ── SCENE DETECTION ───────────────────────────────────────────────
    {
        "name": "detect_scene_changes",
        "description": "Detect scene cuts in a video file using FFprobe. Returns list of timestamps where scene changes occur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "threshold": {"type": "number", "default": 0.3, "description": "0.0-1.0, lower = more sensitive"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "add_scene_cut_markers",
        "description": "Detect scene changes in a video file and automatically add Cyan markers to the timeline at each cut point.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "threshold": {"type": "number", "default": 0.3},
            },
            "required": ["file_path"],
        },
    },
    # ── AI IMAGE GENERATION ───────────────────────────────────────────
    {
        "name": "generate_ai_image",
        "description": "Generate an AI image using DALL-E 3 or Flux. The image is saved to disk and returned with a preview. Use drop_ai_image_to_timeline to place it on the timeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Detailed description of what to generate"},
                "provider": {"type": "string", "default": "auto", "enum": ["auto", "dalle3", "flux"], "description": "auto=best available, dalle3=DALL-E 3, flux=Flux Schnell via fal.ai"},
                "width": {"type": "integer", "default": 1920},
                "height": {"type": "integer", "default": 1080},
                "style": {"type": "string", "default": "cinematic", "description": "cinematic, photorealistic, dramatic, vintage, neon, minimal, etc."},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "drop_ai_image_to_timeline",
        "description": "Add a previously generated AI image (by file path) to the current Resolve timeline at a specific position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the image file"},
                "position_seconds": {"type": "number", "default": -1, "description": "-1 = append to end"},
                "duration_seconds": {"type": "number", "default": 3.0},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "generate_ai_transition",
        "description": "Generate an AI-powered visual transition between two clips. Grabs the last frame of clip A and first frame of clip B, generates a transition frame with AI, then places it between them on the timeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_before_index": {"type": "integer", "default": 0, "description": "0-based index of the clip BEFORE the transition"},
                "clip_after_index": {"type": "integer", "default": 1, "description": "0-based index of the clip AFTER the transition"},
                "transition_style": {"type": "string", "default": "cinematic blend", "description": "e.g. 'cinematic blend', 'light leak', 'film burn', 'dream sequence', 'glitch'"},
                "track": {"type": "integer", "default": 1},
                "duration_seconds": {"type": "number", "default": 2.0},
            },
            "required": [],
        },
    },
    # ── BEAT DETECTION & SYNC EDIT ────────────────────────────────────
    {
        "name": "detect_beats",
        "description": "Analyze an audio or video file and detect beats, BPM, downbeats, and energy peaks using librosa. Returns timestamps to sync cuts to music.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the audio/music file (mp3, wav, aac) or video file with audio"},
                "bpm_hint": {"type": "number", "description": "Optional BPM hint to improve accuracy"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "cut_clips_at_beats",
        "description": "Place razor cuts on the timeline at a list of beat timestamps. Use after detect_beats to sync cuts to music.",
        "input_schema": {
            "type": "object",
            "properties": {
                "beat_times": {"type": "array", "items": {"type": "number"}, "description": "List of timestamps in seconds to cut at"},
                "track": {"type": "integer", "default": 1},
            },
            "required": ["beat_times"],
        },
    },
    {
        "name": "add_beats_as_markers",
        "description": "Add yellow markers at every beat position for visual reference before cutting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "beat_times": {"type": "array", "items": {"type": "number"}},
                "color": {"type": "string", "default": "Yellow"},
            },
            "required": ["beat_times"],
        },
    },
    # ── CLIP TRIMMING & RIPPLE ─────────────────────────────────────────
    {
        "name": "trim_clip_start",
        "description": "Trim the in-point (start) of a clip. Positive trim_seconds removes from the start, negative extends it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
                "trim_seconds": {"type": "number", "description": "Seconds to trim from start (positive=trim in, negative=extend)"},
            },
            "required": ["trim_seconds"],
        },
    },
    {
        "name": "trim_clip_end",
        "description": "Trim the out-point (end) of a clip. Positive trim_seconds removes from the end, negative extends it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
                "trim_seconds": {"type": "number", "description": "Seconds to trim from end"},
            },
            "required": ["trim_seconds"],
        },
    },
    {
        "name": "ripple_delete_clip",
        "description": "Delete a clip and ripple-close the gap so subsequent clips shift left.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "move_clip_to_position",
        "description": "Move a clip to a new start position on the timeline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
                "new_start_seconds": {"type": "number", "description": "New start position in seconds"},
            },
            "required": ["new_start_seconds"],
        },
    },
    {
        "name": "reorder_clips",
        "description": "Reorder clips on a track by specifying the desired order as a list of clip names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "new_order": {"type": "array", "items": {"type": "string"}, "description": "Clip names in desired order"},
            },
            "required": ["new_order"],
        },
    },
    # ── AUTO EDIT PASSES ──────────────────────────────────────────────
    {
        "name": "auto_rough_cut",
        "description": "Trim all clips on a track to a target duration for a quick rough cut pass.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "target_duration_seconds": {"type": "number", "default": 3.0, "description": "Max duration per clip in seconds"},
            },
            "required": [],
        },
    },
    {
        "name": "create_multicam_cut",
        "description": "Create rapid-fire cuts by splitting all clips into equal-length segments. Great for music videos and fast-paced montages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clips_per_second": {"type": "number", "default": 1.0, "description": "How many cuts per second (e.g. 2.0 = cut every 0.5s)"},
            },
            "required": [],
        },
    },
    {
        "name": "apply_cross_dissolve_all",
        "description": "Apply cross dissolve transitions between all clips on a track.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "duration_seconds": {"type": "number", "default": 0.5},
            },
            "required": [],
        },
    },
    {
        "name": "detect_and_cut_silence",
        "description": "Scan the timeline for very short or silent clips and mark them with red markers for review/deletion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "min_silence_db": {"type": "number", "default": -50.0},
                "min_duration_seconds": {"type": "number", "default": 0.5, "description": "Clips shorter than this are flagged"},
            },
            "required": [],
        },
    },
    {
        "name": "color_grade_all_clips",
        "description": "Apply a consistent color grade (contrast, saturation, lift, gain) to ALL clips on a track at once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "contrast": {"type": "number", "default": 1.05},
                "saturation": {"type": "number", "default": 0.95},
                "lift_r": {"type": "number", "default": 0.0},
                "lift_g": {"type": "number", "default": 0.0},
                "lift_b": {"type": "number", "default": 0.02},
                "gain_r": {"type": "number", "default": 0.01},
                "gain_g": {"type": "number", "default": 0.0},
                "gain_b": {"type": "number", "default": -0.01},
            },
            "required": [],
        },
    },
    {
        "name": "normalize_clip_audio",
        "description": "Set a clip's audio level to a target dB value.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
                "target_db": {"type": "number", "default": -12.0, "description": "Target level in dB (-12 for dialogue, -18 for music)"},
            },
            "required": [],
        },
    },
    {
        "name": "set_jl_cut",
        "description": "Create a J-cut: audio from the next clip starts before the video cut for a smoother transition.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
                "audio_lead_seconds": {"type": "number", "default": 0.5},
            },
            "required": [],
        },
    },

    # ── AUDIO ANALYSIS ────────────────────────────────────────────────
    {
        "name": "get_audio_energy",
        "description": "Analyze the loudness and energy of an audio or video file using FFmpeg. Returns mean/max volume in dB and energy level. Use this to find the most energetic clips or detect dead audio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the audio or video file"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "get_waveform_peaks",
        "description": "Divide a file into segments and measure audio energy per segment. Returns the best/most energetic moments — perfect for finding where to cut.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "num_segments": {"type": "integer", "default": 20, "description": "How many segments to analyze"},
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "detect_silence_ranges",
        "description": "Find exact silence ranges in a file using FFmpeg silencedetect. Returns start/end/duration of every silent section — use to precisely cut dead air.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "silence_threshold_db": {"type": "number", "default": -35.0},
                "min_silence_duration": {"type": "number", "default": 0.5},
            },
            "required": ["file_path"],
        },
    },

    # ── CLIP INTELLIGENCE ─────────────────────────────────────────────
    {
        "name": "score_clips",
        "description": "Score and rank all clips on the timeline based on name keywords, duration, and position. Returns keeper/review/cut recommendations. Use before a rough cut to understand what you're working with.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline_info": {"type": "object", "description": "Pass the result of get_timeline_info() here"},
            },
            "required": ["timeline_info"],
        },
    },
    {
        "name": "analyze_hook_strength",
        "description": "Analyze the first 3-5 seconds of the edit for social media hook strength. Returns a score and specific suggestions to improve retention.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline_info": {"type": "object"},
            },
            "required": ["timeline_info"],
        },
    },
    {
        "name": "generate_chapter_markers",
        "description": "Generate YouTube-ready chapter timestamps from timeline markers. Returns formatted text ready to paste into a YouTube description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline_info": {"type": "object"},
            },
            "required": ["timeline_info"],
        },
    },
    {
        "name": "export_edit_summary",
        "description": "Export a complete edit summary with all clips, timecodes, durations, and markers. Great for client deliverables, EDLs, and shot logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
            },
            "required": [],
        },
    },

    # ── ADVANCED EDITING ──────────────────────────────────────────────
    {
        "name": "ripple_delete_all_gaps",
        "description": "Remove all empty gaps between clips on a track in one pass.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
            },
            "required": [],
        },
    },
    {
        "name": "set_clip_zoom",
        "description": "Punch in / zoom on a specific clip for visual variety. scale=1.2 is 20% zoom. Use x/y to reframe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
                "scale": {"type": "number", "default": 1.2, "description": "1.0=normal, 1.2=20% zoom in"},
                "x": {"type": "number", "default": 0.0, "description": "Horizontal pan offset"},
                "y": {"type": "number", "default": 0.0, "description": "Vertical tilt offset"},
            },
            "required": [],
        },
    },
    {
        "name": "set_clip_zoom_all",
        "description": "Add subtle zoom variation to all clips on a track for a dynamic feel. Alternates between zoom-in and pan for variety.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "scale": {"type": "number", "default": 1.15},
                "alternate": {"type": "boolean", "default": True, "description": "Alternate zoom direction between clips"},
            },
            "required": [],
        },
    },
    {
        "name": "auto_duck_music",
        "description": "Automatically lower music volume under dialogue clips (audio ducking). Lowers music wherever dialogue exists, restores it in gaps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialogue_track": {"type": "integer", "default": 1},
                "music_track": {"type": "integer", "default": 2},
                "normal_music_db": {"type": "number", "default": -18.0},
                "duck_db": {"type": "number", "default": -30.0},
                "fade_seconds": {"type": "number", "default": 0.5},
            },
            "required": [],
        },
    },
    {
        "name": "move_clips_to_broll_track",
        "description": "Move B-roll / cutaway clips from track 1 to track 2 based on their names. Automatically creates a proper A/B-roll structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords that identify B-roll clips. Defaults to common B-roll keywords."},
                "source_track": {"type": "integer", "default": 1},
                "dest_track": {"type": "integer", "default": 2},
            },
            "required": [],
        },
    },
    {
        "name": "smart_trim_to_duration",
        "description": "Trim the entire edit down to a target duration using a strategy: trim_ends (proportional trim), remove_short (delete shortest clips), remove_scored (delete weakest clips).",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_seconds": {"type": "number", "description": "Target duration in seconds (e.g. 60 for a 1-min cut)"},
                "track": {"type": "integer", "default": 1},
                "strategy": {"type": "string", "default": "trim_ends", "enum": ["trim_ends", "remove_short", "remove_scored"]},
            },
            "required": ["target_seconds"],
        },
    },
    {
        "name": "apply_speed_ramp",
        "description": "Apply a speed ramp to a clip — speeds up and slows down at different points. Default creates a slow-motion middle section. Great for dramatic moments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
                "ramp_points": {
                    "type": "array",
                    "description": "List of speed keypoints: [{position: 0.0-1.0, speed: 0.1-2.0}]",
                    "items": {
                        "type": "object",
                        "properties": {
                            "position": {"type": "number"},
                            "speed": {"type": "number"},
                        }
                    }
                },
            },
            "required": [],
        },
    },
    {
        "name": "normalize_all_audio",
        "description": "Normalize every clip's audio on a track to a target dB level in one pass.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "default": 1},
                "target_db": {"type": "number", "default": -12.0},
            },
            "required": [],
        },
    },
    {
        "name": "add_text_title",
        "description": "Add a text title or lower third to the timeline. Note: requires manual placement in the Titles panel for full formatting control.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "start_seconds": {"type": "number", "default": 0.0},
                "duration_seconds": {"type": "number", "default": 3.0},
                "track": {"type": "integer", "default": 2},
                "style": {"type": "string", "default": "lower_third", "enum": ["lower_third", "full_screen", "subtitle"]},
            },
            "required": ["text"],
        },
    },

    # ── SMART ASSEMBLY ────────────────────────────────────────────────
    {
        "name": "plan_assembly_from_brief",
        "description": (
            "Given a list of media pool clips and a creative brief, generate a complete assembly plan "
            "with clip order, timing, and grade suggestions. "
            "Example briefs: '60s hype reel that builds energy', 'emotional documentary opener', "
            "'30s social media cut for Instagram'. "
            "WORKFLOW: call get_media_pool_clips() first, then pass clips + brief here, "
            "then call assemble_clips_to_timeline() with the returned assembly_plan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "media_pool_clips": {
                    "type": "array",
                    "description": "Pass the clips array from get_media_pool_clips()",
                },
                "brief": {
                    "type": "string",
                    "description": "Creative brief describing the edit (e.g. '60s hype reel that builds energy and ends on a wide shot')",
                },
                "target_duration": {
                    "type": "number",
                    "default": 60.0,
                    "description": "Target total edit duration in seconds",
                },
                "style": {
                    "type": "string",
                    "default": "balanced",
                    "enum": ["hype", "emotional", "corporate", "documentary", "balanced"],
                    "description": "Edit style — auto-detected from brief if not specified",
                },
            },
            "required": ["media_pool_clips", "brief"],
        },
    },
    {
        "name": "assemble_clips_to_timeline",
        "description": (
            "Build a timeline edit from a smart assembly plan. "
            "Call plan_assembly_from_brief() first, then pass its assembly_plan here. "
            "Imports each clip from disk and appends to the timeline with suggested durations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assembly_plan": {
                    "type": "array",
                    "description": "The assembly_plan array returned by plan_assembly_from_brief()",
                },
                "clear_existing": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, clears the existing timeline before building",
                },
                "track": {"type": "integer", "default": 1},
            },
            "required": ["assembly_plan"],
        },
    },
]
