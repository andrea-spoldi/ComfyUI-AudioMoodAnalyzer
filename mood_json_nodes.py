import json

_LOG = "[AudioMoodAnalyzer]"

_UNPACK_FIELDS = [
    "sonic_mood",
    "energy_profile",
    "tension_profile",
    "color_palette",
    "lighting_implications",
    "texture_implications",
    "composition_suggestions",
    "avoid",
]


def _join_field(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


class MoodJsonUnpacker:
    CATEGORY = "audio/mood"
    FUNCTION = "unpack"
    RETURN_TYPES = tuple("STRING" for _ in _UNPACK_FIELDS)
    RETURN_NAMES = tuple(_UNPACK_FIELDS)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"mood_json": ("STRING", {"default": ""})}}

    def unpack(self, mood_json):
        try:
            data = json.loads(mood_json) if mood_json.strip() else {}
        except json.JSONDecodeError:
            data = {}
        return tuple(_join_field(data[f]) if f in data else "" for f in _UNPACK_FIELDS)


NODE_CLASS_MAPPINGS = {
    "MoodJsonUnpacker": MoodJsonUnpacker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MoodJsonUnpacker": "Mood JSON Unpacker",
}
