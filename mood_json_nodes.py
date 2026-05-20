import json

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


_DEFAULT_FIELDS = "color_palette\nlighting_implications\ntexture_implications"


class PromptEnricher:
    CATEGORY = "audio/mood"
    FUNCTION = "enrich"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("enriched_prompt",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "mood_json": ("STRING", {"default": ""}),
                "fields_to_inject": ("STRING", {
                    "multiline": True,
                    "default": _DEFAULT_FIELDS,
                }),
            }
        }

    def enrich(self, prompt, mood_json, fields_to_inject):
        try:
            data = json.loads(mood_json) if mood_json.strip() else {}
        except json.JSONDecodeError:
            return (prompt,)

        fields = [f.strip() for f in fields_to_inject.splitlines() if f.strip()]
        result = prompt
        for field in fields:
            value = data.get(field)
            if value is None:
                continue
            joined = _join_field(value)
            if not joined:
                continue
            if field == "avoid":
                suffix = f", avoid: {joined}"
            else:
                suffix = f", {joined}"
            result = result + suffix if result else joined
        return (result,)


NODE_CLASS_MAPPINGS = {
    "MoodJsonUnpacker": MoodJsonUnpacker,
    "PromptEnricher": PromptEnricher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MoodJsonUnpacker": "Mood JSON Unpacker",
    "PromptEnricher": "Prompt Enricher",
}
