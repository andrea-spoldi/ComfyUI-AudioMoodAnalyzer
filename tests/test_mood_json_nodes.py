import sys, unittest
from unittest.mock import MagicMock
import json

# Stub heavy dependencies so importing mood_json_nodes never fails in CI
for mod in ["librosa", "soundfile", "numpy", "torch", "transformers"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import mood_json_nodes as mjn


FULL_MOOD = {
    "sonic_mood": ["melancholic", "dense"],
    "energy_profile": "low sustained energy",
    "tension_profile": "high internal tension",
    "color_palette": ["deep blue", "charcoal"],
    "lighting_implications": ["underlit", "side-lit"],
    "texture_implications": ["rough", "worn"],
    "composition_suggestions": ["wide shot", "negative space"],
    "avoid": ["bright colours", "sharp edges"],
}


class TestMoodJsonUnpacker(unittest.TestCase):
    def setUp(self):
        self.node = mjn.MoodJsonUnpacker()

    def _run(self, mood_json):
        result = self.node.unpack(mood_json=mood_json)
        keys = mjn.MoodJsonUnpacker.RETURN_NAMES
        return dict(zip(keys, result))

    def test_all_fields_returned(self):
        out = self._run(json.dumps(FULL_MOOD))
        self.assertEqual(out["sonic_mood"], "melancholic, dense")
        self.assertEqual(out["energy_profile"], "low sustained energy")
        self.assertEqual(out["tension_profile"], "high internal tension")
        self.assertEqual(out["color_palette"], "deep blue, charcoal")
        self.assertEqual(out["lighting_implications"], "underlit, side-lit")
        self.assertEqual(out["texture_implications"], "rough, worn")
        self.assertEqual(out["composition_suggestions"], "wide shot, negative space")
        self.assertEqual(out["avoid"], "bright colours, sharp edges")

    def test_list_fields_joined_with_comma_space(self):
        mood = {"sonic_mood": ["a", "b", "c"]}
        out = self._run(json.dumps(mood))
        self.assertEqual(out["sonic_mood"], "a, b, c")

    def test_missing_key_returns_empty_string(self):
        out = self._run(json.dumps({}))
        for key in mjn.MoodJsonUnpacker.RETURN_NAMES:
            self.assertEqual(out[key], "")

    def test_malformed_json_returns_all_empty(self):
        out = self._run("not valid json {{")
        for key in mjn.MoodJsonUnpacker.RETURN_NAMES:
            self.assertEqual(out[key], "")

    def test_empty_string_input_returns_all_empty(self):
        out = self._run("")
        for key in mjn.MoodJsonUnpacker.RETURN_NAMES:
            self.assertEqual(out[key], "")

    def test_non_list_value_coerced_to_string(self):
        mood = {"energy_profile": 42}
        out = self._run(json.dumps(mood))
        self.assertEqual(out["energy_profile"], "42")


class TestPromptEnricher(unittest.TestCase):
    def setUp(self):
        self.node = mjn.PromptEnricher()

    def _run(self, prompt, mood_json, fields_to_inject):
        result = self.node.enrich(
            prompt=prompt,
            mood_json=mood_json,
            fields_to_inject=fields_to_inject,
        )
        return result[0]  # single STRING output

    def test_default_fields_appended(self):
        mood = json.dumps({
            "color_palette": ["deep blue", "charcoal"],
            "lighting_implications": ["underlit"],
            "texture_implications": ["rough"],
        })
        out = self._run("a dark figure", mood, "color_palette\nlighting_implications\ntexture_implications")
        self.assertIn("deep blue, charcoal", out)
        self.assertIn("underlit", out)
        self.assertIn("rough", out)
        self.assertTrue(out.startswith("a dark figure"))

    def test_avoid_field_prefixed(self):
        mood = json.dumps({"avoid": ["bright colours", "sharp edges"]})
        out = self._run("base prompt", mood, "avoid")
        self.assertIn("avoid: bright colours, sharp edges", out)

    def test_unknown_field_silently_skipped(self):
        mood = json.dumps({"color_palette": ["red"]})
        out = self._run("base", mood, "color_palette\nnonexistent_field")
        self.assertIn("red", out)
        self.assertNotIn("nonexistent_field", out)

    def test_malformed_json_returns_prompt_unchanged(self):
        out = self._run("unchanged prompt", "{{bad json", "color_palette")
        self.assertEqual(out, "unchanged prompt")

    def test_empty_prompt_returns_injected_fields_only(self):
        mood = json.dumps({"color_palette": ["red", "black"]})
        out = self._run("", mood, "color_palette")
        self.assertIn("red, black", out)

    def test_empty_fields_to_inject_returns_prompt_unchanged(self):
        mood = json.dumps({"color_palette": ["red"]})
        out = self._run("base prompt", mood, "")
        self.assertEqual(out, "base prompt")

    def test_empty_list_field_skipped(self):
        mood = json.dumps({"color_palette": [], "lighting_implications": ["side-lit"]})
        out = self._run("base", mood, "color_palette\nlighting_implications")
        self.assertNotIn("color_palette", out)
        self.assertIn("side-lit", out)

    def test_injection_order_follows_fields_to_inject(self):
        mood = json.dumps({
            "color_palette": ["blue"],
            "lighting_implications": ["dark"],
        })
        out = self._run("base", mood, "lighting_implications\ncolor_palette")
        idx_lighting = out.index("dark")
        idx_color = out.index("blue")
        self.assertLess(idx_lighting, idx_color)


if __name__ == "__main__":
    unittest.main()
