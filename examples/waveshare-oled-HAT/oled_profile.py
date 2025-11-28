MAX_TEXT_LENGTH = 16

CAPPABILITIES_SENSORS = [
    {
        "id": "cpu_temp",
        "display_name": "CPU temperature",
        "sensor_type": "temperature",
        "data_source": {"sensor_type": "temperature", "path": "data"},
        "measures": [
            {
                "key": "temperature_c",
                "display_name": "Temperature",
                "unit": "C",
                "value_type": "number",
                "precision": 2,
            }
        ],
    }
]

CAPABILITIES = {
    "sensors": CAPPABILITIES_SENSORS,
    "commands": [
        {
            "id": "trigger_data",
            "display_name": "Trigger measurement",
            "command_type": "trigger-data",
            "topic_suffix": "commands/trigger-data",
            "parameters": [],
        },
        {
            "id": "display_text",
            "display_name": "Display text",
            "command_type": "action",
            "topic_suffix": "commands/action",
            "parameters": [
                {
                    "name": "text",
                    "display_name": "Text",
                    "type": "string",
                    "required": True,
                },
                {
                    "name": "line",
                    "display_name": "Line (0-7)",
                    "type": "integer",
                    "required": False,
                    "default": 0,
                    "min": 0,
                    "max": 7,
                },
                {
                    "name": "clear",
                    "display_name": "Clear before writing",
                    "type": "boolean",
                    "required": False,
                    "default": True,
                },
            ],
        },
        {
            "id": "clear_display",
            "display_name": "Clear display",
            "command_type": "action",
            "topic_suffix": "commands/action",
            "parameters": [],
        },
        {
            "id": "light",
            "display_name": "Onboard LED",
            "command_type": "light",
            "topic_suffix": "commands/light",
            "parameters": [
                {
                    "name": "state",
                    "display_name": "State",
                    "type": "enum",
                    "values": ["on", "off", "toggle"],
                    "required": True,
                    "default": "on",
                }
            ],
        },
    ],
    "ui_hints": {
        "layout": [
            {
                "type": "sensor_panel",
                "sensor_id": "cpu_temp",
                "title": "CPU temperature",
                "primary_measure": "temperature_c",
                "chart": {
                    "enabled": True,
                    "window_minutes": 60,
                },
            },
            {
                "type": "commands_panel",
                "title": "Display",
                "commands": ["display_text", "clear_display"],
            },
            {
                "type": "commands_panel",
                "title": "Control",
                "commands": ["light"],
            },
        ]
    },
}


def sanitize_text_for_display(text: str) -> str:
    """Convert text to something the 8x8 ASCII font can show.

    - Swedish letters åäöÅÄÖ are transliterated to a/o/A/O.
    - All other characters outside ASCII 32-126 raise ValueError.
    """

    replacements = {
        "å": "a",
        "ä": "a",
        "ö": "o",
        "Å": "A",
        "Ä": "A",
        "Ö": "O",
    }

    result_chars = []
    for char in text:
        if char in replacements:
            char = replacements[char]
        code = ord(char)
        if 32 <= code <= 126:
            result_chars.append(char)
        else:
            raise ValueError("Text contains characters not supported by the display")
    return "".join(result_chars)
