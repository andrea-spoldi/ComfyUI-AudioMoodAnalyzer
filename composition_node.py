import json
import time

from .shared import (
    _LOG,
    _fmt_json,
    _parse_resolution,
    _COMPOSITION_FALLBACK,
    _timed_generate,
    _extract_json,
)


class CompositionInferenceNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mood_json": ("STRING", {"multiline": True}),
                "subject_json": ("STRING", {"multiline": True}),
                "ollama_url": ("STRING", {
                    "default": "http://localhost:11434/api/generate"
                }),
                "model": ("STRING", {"default": "qwen3:14b"}),
                "analysis_temperature": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.5, "step": 0.1
                }),
                "prompt_temperature": ("FLOAT", {
                    "default": 0.8, "min": 0.0, "max": 1.5, "step": 0.1
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("composition_json", "composition_prompt", "width", "height")
    FUNCTION = "infer"
    CATEGORY = "audio/analysis"

    def _build_composition_json_prompt(self, mood_json, subject_json):
        subject_section = (
            f"Subject analysis (primary signal — inferred from lyrics, focus fragments, or song description):\n{_fmt_json(subject_json)}"
            if subject_json
            else "Subject analysis: not available — infer from mood alone, default to environment_dominant framing."
        )
        return f"""
You are an art director inferring visual composition from music analysis and lyrical subject material.

{subject_section}

Sonic mood analysis (supporting atmospheric context):
{_fmt_json(mood_json)}

Infer the optimal visual composition for an image that expresses this music.

Consider:
- Does the subject dominate, or does the environment carry the weight?
- What orientation and ratio best serves the emotional content?
- Where does the subject sit within the frame?
- How much negative space reinforces the mood?
- What camera distance and crop serve the subject?

Return only valid JSON with this exact structure:
{{
  "aspect_ratio": {{
    "orientation": "portrait",
    "ratio": "4:5",
    "recommended_resolution": "1024x1280"
  }},
  "subject_placement": {{
    "position": "lower_right",
    "size_weight": 0.35
  }},
  "environment": {{
    "weight": 0.65,
    "negative_space": "high"
  }},
  "camera": {{
    "distance": "medium",
    "framing_style": "environment_dominant",
    "crop": "waist_up"
  }}
}}

Constraints:
- orientation must be one of: portrait, landscape, square
- ratio must be one of: 4:5, 16:9, 9:16, 1:1, 3:2, 2:3
- recommended_resolution must be one of: 1024x1280, 1280x1024, 768x1344, 1344x768, 896x1152, 1152x896, 1024x1024, 832x1216, 1216x832
- position must be one of: center, lower_left, lower_right, upper_left, upper_right, off_frame
- negative_space must be one of: low, medium, high
- distance must be one of: close, medium, wide
- framing_style must be one of: subject_dominant, environment_dominant, balanced
- crop must be one of: full_body, waist_up, bust, face_only, none

If subject analysis is unavailable, set framing_style to environment_dominant and crop to none.

Do not include any text before or after the JSON.
"""

    def _build_composition_prose_request(self, composition_json):
        return f"""
You are an art director translating a composition analysis into image-generation prompt language.

Composition analysis:
{_fmt_json(composition_json)}

Write a short, precise image-generation prompt that describes:
- the framing and orientation
- where the subject sits in the frame (if present)
- the relationship between subject and environment
- camera distance and crop
- negative space quality

Keep it:
- concise (one to two sentences)
- visual and specific
- in image-generation prompt style (no explanation, no metadata)

Output only the final composition prompt.
"""

    def infer(
        self,
        mood_json,
        subject_json,
        ollama_url,
        model,
        analysis_temperature,
        prompt_temperature,
    ):
        t0 = time.time()
        print(f"{_LOG} [Composition] model: {model}")

        try:
            mood = json.loads(mood_json) if isinstance(mood_json, str) else mood_json
        except (json.JSONDecodeError, TypeError):
            mood = {}

        try:
            subject = json.loads(subject_json) if isinstance(subject_json, str) else subject_json
        except (json.JSONDecodeError, TypeError):
            subject = {}

        if not subject:
            print(f"{_LOG} [Composition] ⚠ subject_json empty — inferring from mood only")

        raw_composition = _timed_generate(
            "composition inference", ollama_url, model,
            self._build_composition_json_prompt(mood, subject),
            analysis_temperature,
        )
        composition = _extract_json(raw_composition)

        if "error" in composition:
            print(f"{_LOG} [Composition] ⚠ falling back to safe composition defaults")
            composition = _COMPOSITION_FALLBACK

        width, height = _parse_resolution(
            composition.get("aspect_ratio", {}).get("recommended_resolution", "1024x1024")
        )

        composition_prompt = _timed_generate(
            "composition prompt", ollama_url, model,
            self._build_composition_prose_request(composition),
            prompt_temperature,
        )

        if not composition_prompt.strip():
            print(f"{_LOG} [Composition] ⚠ empty composition prompt returned")

        print(f"{_LOG} [Composition] done  total: {time.time()-t0:.1f}s")

        return (
            _fmt_json(composition),
            composition_prompt,
            width,
            height,
        )


NODE_CLASS_MAPPINGS = {
    "CompositionInferenceNode": CompositionInferenceNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CompositionInferenceNode": "Composition Inference",
}
