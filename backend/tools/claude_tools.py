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
                "time_seconds": {"type": "number", "description": "Timestamp in seconds"}
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
                "time_seconds": {"type": "number", "description": "Timestamp in seconds to jump to"}
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
                "time_seconds": {"type": "number", "description": "Where to make the cut (seconds)"},
                "track": {"type": "integer", "default": 1, "description": "Video track number (1-based)"},
            },
            "required": ["time_seconds"],
        },
    },
    {
        "name": "delete_clips_in_range",
        "description": "Delete all video clips within a time range on a track. Use this to remove dead air, bad takes, or unwanted sections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_seconds": {"type": "number", "description": "Range start in seconds"},
                "end_seconds": {"type": "number", "description": "Range end in seconds"},
                "track": {"type": "integer", "default": 1, "description": "Video track number (1-based)"},
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
                "color": {
                    "type": "string",
                    "description": "Orange, Apricot, Yellow, Lime, Green, Teal, Navy, Blue, Purple, Violet, Pink, Tan, Beige, Brown, Chocolate",
                },
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
                "media_path": {"type": "string", "description": "Absolute path to the media file"},
                "start_seconds": {"type": "number", "description": "In-point in the source clip (seconds)", "default": 0},
                "end_seconds": {"type": "number", "description": "Out-point in the source clip (seconds, optional)"},
            },
            "required": ["media_path"],
        },
    },
    {
        "name": "get_media_pool_clips",
        "description": "List all clips currently in the DaVinci Resolve media pool with their file paths, duration, and resolution.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    # ── COLOR GRADING ─────────────────────────────────────────────────
    {
        "name": "apply_color_wheel",
        "description": "Adjust the Lift, Gamma, Gain, or Offset color wheel on a clip. Use to shift shadows, mids, highlights, or overall color cast. Values -1.0 to 1.0 (0 = no change).",
        "input_schema": {
            "type": "object",
            "properties": {
                "wheel": {
                    "type": "string",
                    "description": "Which wheel to adjust: lift (shadows), gamma (mids), gain (highlights), offset (all)",
                    "enum": ["lift", "gamma", "gain", "offset"],
                },
                "red": {"type": "number", "default": 0.0, "description": "-1.0 to 1.0"},
                "green": {"type": "number", "default": 0.0, "description": "-1.0 to 1.0"},
                "blue": {"type": "number", "default": 0.0, "description": "-1.0 to 1.0"},
                "luma": {"type": "number", "default": 0.0, "description": "Master luminance offset -1.0 to 1.0"},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0, "description": "0-based clip index on the track"},
            },
            "required": ["wheel"],
        },
    },
    {
        "name": "set_contrast_saturation",
        "description": "Set contrast and saturation on a clip. 1.0 = normal/no change. Contrast range 0.0-2.0, Saturation range 0.0-2.0.",
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
                "lut_path": {"type": "string", "description": "Absolute path to the .cube LUT file"},
                "track": {"type": "integer", "default": 1},
                "clip_index": {"type": "integer", "default": 0},
            },
            "required": ["lut_path"],
        },
    },
    {
        "name": "add_serial_node",
        "description": "Add a new serial correction node to a clip's color node graph.",
        "input_schema": {
            "type": "object",
            "properties": {
                "label": {"type": "string", "default": "New Node", "description": "Label for the node"},
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
    # ── AUDIO ─────────────────────────────────────────────────────────
    {
        "name": "set_audio_track_volume",
        "description": "Set the volume of an entire audio track in dB. 0 dB = unity gain. Use negative values to reduce volume.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Audio track number (1-based)"},
                "volume_db": {"type": "number", "description": "Volume in dB. 0 = unity, -6 = half, -∞ = silent"},
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
    # ── RENDER ────────────────────────────────────────────────────────
    {
        "name": "get_render_presets",
        "description": "List all available render presets in the current project.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "start_render",
        "description": "Start rendering the timeline to a file using a render preset.",
        "input_schema": {
            "type": "object",
            "properties": {
                "preset_name": {"type": "string", "description": "Name of the render preset to use"},
                "output_path": {"type": "string", "description": "Absolute directory path for output file"},
            },
            "required": ["preset_name", "output_path"],
        },
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
]
