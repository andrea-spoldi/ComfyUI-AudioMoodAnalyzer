import json
import sys, os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Stub heavy dependencies before import
for mod in ["librosa", "soundfile", "numpy", "transformers"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import fear_of_the_art_audio_analyzer.composition_node as ama
from fear_of_the_art_audio_analyzer.shared import _parse_resolution


_MOOD_JSON = json.dumps({
    "sonic_mood": ["dark", "tense"],
    "energy_profile": "sustained",
    "tension_profile": "high",
    "visual_environment_implications": ["dim interior"],
    "lighting_implications": ["low key"],
    "color_palette": ["grey", "black"],
    "texture_implications": ["rough"],
    "subject_presence": ["solitary figure"],
    "composition_suggestions": ["off-centre"],
    "motion_feel": ["slow"],
    "camera_language": ["close"],
    "avoid": [],
})

_SUBJECT_JSON = json.dumps({
    "archetype": "solitary figure",
    "emotional_state": "grief",
    "posture": "hunched",
    "gaze": "downward",
    "symbolic_attributes": ["worn coat"],
    "avoid": [],
})

_COMPOSITION_LLM_RESPONSE = json.dumps({
    "aspect_ratio": {
        "orientation": "portrait",
        "ratio": "4:5",
        "recommended_resolution": "1024x1280",
    },
    "subject_placement": {"position": "lower_right", "size_weight": 0.35},
    "environment": {"weight": 0.65, "negative_space": "high"},
    "camera": {"distance": "medium", "framing_style": "environment_dominant", "crop": "waist_up"},
})

_PROSE_RESPONSE = "lower-right figure, waist-up crop, environment-dominant frame, high negative space"


def _make_node():
    return ama.CompositionInferenceNode()


def _run(node, mood=_MOOD_JSON, subject=_SUBJECT_JSON,
         llm_side_effect=None, llm_returns=None):
    """Call node.infer with _timed_generate mocked."""
    if llm_side_effect is not None:
        mock_gen = MagicMock(side_effect=llm_side_effect)
    else:
        mock_gen = MagicMock(side_effect=llm_returns or [_COMPOSITION_LLM_RESPONSE, _PROSE_RESPONSE])
    with patch('fear_of_the_art_audio_analyzer.composition_node._timed_generate', mock_gen):
        return node.infer(
            mood_json=mood,
            subject_json=subject,
            ollama_url="http://localhost:11434/api/generate",
            model="qwen3:14b",
            analysis_temperature=0.4,
            prompt_temperature=0.8,
        )


class TestParseResolution(unittest.TestCase):
    def test_ascii_x_separator(self):
        self.assertEqual(_parse_resolution("1024x1280"), (1024, 1280))

    def test_unicode_times_separator(self):
        self.assertEqual(_parse_resolution("1024×1280"), (1024, 1280))

    def test_square(self):
        self.assertEqual(_parse_resolution("1024x1024"), (1024, 1024))

    def test_whitespace_around_values(self):
        self.assertEqual(_parse_resolution(" 832 x 1216 "), (832, 1216))

    def test_none_input_returns_default(self):
        self.assertEqual(_parse_resolution(None), (1024, 1024))

    def test_garbage_string_returns_default(self):
        self.assertEqual(_parse_resolution("not_a_resolution"), (1024, 1024))

    def test_unicode_separator_tried_before_ascii(self):
        # "1024×1280" contains × but not x — should parse correctly
        w, h = _parse_resolution("1024×1280")
        self.assertEqual((w, h), (1024, 1280))


class TestCompositionInferenceNodeMeta(unittest.TestCase):
    def test_return_types(self):
        self.assertEqual(
            ama.CompositionInferenceNode.RETURN_TYPES,
            ("STRING", "STRING", "INT", "INT"),
        )

    def test_return_names(self):
        self.assertEqual(
            ama.CompositionInferenceNode.RETURN_NAMES,
            ("composition_json", "composition_prompt", "width", "height"),
        )

    def test_function_name(self):
        self.assertEqual(ama.CompositionInferenceNode.FUNCTION, "infer")

    def test_category(self):
        self.assertEqual(ama.CompositionInferenceNode.CATEGORY, "audio/analysis")

    def test_input_types_has_required_inputs(self):
        it = ama.CompositionInferenceNode.INPUT_TYPES()
        required = it["required"]
        for key in ("mood_json", "subject_json", "ollama_url", "model",
                    "analysis_temperature", "prompt_temperature"):
            self.assertIn(key, required)

    def test_registered_in_node_class_mappings(self):
        self.assertIn("CompositionInferenceNode", ama.NODE_CLASS_MAPPINGS)
        self.assertIs(ama.NODE_CLASS_MAPPINGS["CompositionInferenceNode"], ama.CompositionInferenceNode)

    def test_registered_in_display_name_mappings(self):
        self.assertIn("CompositionInferenceNode", ama.NODE_DISPLAY_NAME_MAPPINGS)
        self.assertEqual(
            ama.NODE_DISPLAY_NAME_MAPPINGS["CompositionInferenceNode"],
            "Composition Inference",
        )


class TestCompositionInferenceNodeHappyPath(unittest.TestCase):
    def setUp(self):
        self.node = _make_node()
        self.comp_json, self.comp_prompt, self.width, self.height = _run(self.node)

    def test_composition_json_is_valid_json(self):
        data = json.loads(self.comp_json)
        self.assertIsInstance(data, dict)

    def test_composition_json_has_all_required_keys(self):
        data = json.loads(self.comp_json)
        self.assertIn("aspect_ratio", data)
        self.assertIn("subject_placement", data)
        self.assertIn("environment", data)
        self.assertIn("camera", data)

    def test_aspect_ratio_has_required_sub_keys(self):
        data = json.loads(self.comp_json)
        ar = data["aspect_ratio"]
        self.assertIn("orientation", ar)
        self.assertIn("ratio", ar)
        self.assertIn("recommended_resolution", ar)

    def test_orientation_is_allowed_value(self):
        data = json.loads(self.comp_json)
        self.assertIn(data["aspect_ratio"]["orientation"], {"portrait", "landscape", "square"})

    def test_width_is_positive_int(self):
        self.assertIsInstance(self.width, int)
        self.assertGreater(self.width, 0)

    def test_height_is_positive_int(self):
        self.assertIsInstance(self.height, int)
        self.assertGreater(self.height, 0)

    def test_width_height_match_recommended_resolution(self):
        data = json.loads(self.comp_json)
        res = data["aspect_ratio"]["recommended_resolution"]
        expected_w, expected_h = _parse_resolution(res)
        self.assertEqual(self.width, expected_w)
        self.assertEqual(self.height, expected_h)

    def test_composition_prompt_is_non_empty_string(self):
        self.assertIsInstance(self.comp_prompt, str)
        self.assertTrue(self.comp_prompt.strip())

    def test_two_ollama_calls_made(self):
        node = _make_node()
        mock_gen = MagicMock(side_effect=[_COMPOSITION_LLM_RESPONSE, _PROSE_RESPONSE])
        with patch('fear_of_the_art_audio_analyzer.composition_node._timed_generate', mock_gen):
            node.infer(
                mood_json=_MOOD_JSON, subject_json=_SUBJECT_JSON,
                ollama_url="http://localhost:11434/api/generate",
                model="qwen3:14b", analysis_temperature=0.4, prompt_temperature=0.8,
            )
        self.assertEqual(mock_gen.call_count, 2)

    def test_first_call_uses_analysis_temperature(self):
        node = _make_node()
        calls = []
        def capture(*args, **kwargs):
            # _timed_generate(label, ollama_url, model, prompt, temperature, num_predict=-1)
            calls.append(kwargs.get("temperature", args[4] if len(args) > 4 else None))
            return [_COMPOSITION_LLM_RESPONSE, _PROSE_RESPONSE][len(calls) - 1]
        with patch('fear_of_the_art_audio_analyzer.composition_node._timed_generate', side_effect=capture):
            node.infer(
                mood_json=_MOOD_JSON, subject_json=_SUBJECT_JSON,
                ollama_url="http://localhost:11434/api/generate",
                model="qwen3:14b", analysis_temperature=0.4, prompt_temperature=0.8,
            )
        self.assertEqual(calls[0], 0.4)
        self.assertEqual(calls[1], 0.8)


class TestCompositionInferenceNodeFallback(unittest.TestCase):
    def test_malformed_llm_response_uses_fallback_json(self):
        node = _make_node()
        comp_json, _, width, height = _run(
            node,
            llm_returns=["not valid json at all", _PROSE_RESPONSE],
        )
        data = json.loads(comp_json)
        self.assertIn("aspect_ratio", data)
        self.assertEqual(width, 1024)
        self.assertEqual(height, 1024)

    def test_fallback_orientation_is_square(self):
        node = _make_node()
        comp_json, _, _, _ = _run(
            node,
            llm_returns=["not valid json at all", _PROSE_RESPONSE],
        )
        data = json.loads(comp_json)
        self.assertEqual(data["aspect_ratio"]["orientation"], "square")

    def test_empty_subject_json_does_not_raise(self):
        node = _make_node()
        try:
            _run(node, subject="{}")
        except Exception as exc:
            self.fail(f"infer raised {exc} on empty subject_json")

    def test_empty_subject_json_string_does_not_raise(self):
        node = _make_node()
        try:
            _run(node, subject="")
        except Exception as exc:
            self.fail(f"infer raised {exc} on empty string subject_json")

    def test_malformed_mood_json_does_not_raise(self):
        node = _make_node()
        try:
            _run(node, mood="this is not json")
        except Exception as exc:
            self.fail(f"infer raised {exc} on malformed mood_json")

    def test_empty_composition_prompt_returned_as_string(self):
        node = _make_node()
        _, comp_prompt, _, _ = _run(
            node,
            llm_returns=[_COMPOSITION_LLM_RESPONSE, ""],
        )
        self.assertIsInstance(comp_prompt, str)


if __name__ == "__main__":
    unittest.main()
