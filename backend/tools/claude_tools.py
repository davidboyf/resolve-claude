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
]
