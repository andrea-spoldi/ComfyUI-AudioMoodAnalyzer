# MoodJsonUnpacker + PromptEnricher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new ComfyUI nodes — `MoodJsonUnpacker` (exposes individual mood_json fields as ComfyUI outputs) and `PromptEnricher` (deterministically appends selected mood fields to any prompt) — in a dedicated module file.

**Architecture:** Both nodes live in a new `mood_json_nodes.py` file alongside `audio_mood_analyzer.py`. `__init__.py` is updated to merge both mapping dicts. No changes to `audio_mood_analyzer.py` — zero risk of breaking existing slot indices.

**Tech Stack:** Python 3.x, stdlib `json`, ComfyUI custom node conventions, `unittest`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `mood_json_nodes.py` | `MoodJsonUnpacker` + `PromptEnricher` classes + their mappings |
| Create | `tests/test_mood_json_nodes.py` | All tests for both nodes |
| Modify | `__init__.py` | Merge mappings from both modules |
| Modify | `CLAUDE.md` | Add architecture note about per-file modules |

---

### Task 1: MoodJsonUnpacker — tests

**Files:**
- Create: `tests/test_mood_json_nodes.py`

- [ ] **Step 1: Create the test file with all MoodJsonUnpacker tests**

```python
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
        # returns tuple matching RETURN_NAMES order
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer
python -m pytest tests/test_mood_json_nodes.py -v
```

Expected: `ModuleNotFoundError: No module named 'mood_json_nodes'`

---

### Task 2: MoodJsonUnpacker — implementation

**Files:**
- Create: `mood_json_nodes.py`

- [ ] **Step 1: Create mood_json_nodes.py with MoodJsonUnpacker**

```python
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
```

- [ ] **Step 2: Run MoodJsonUnpacker tests**

```bash
python -m pytest tests/test_mood_json_nodes.py -v
```

Expected: all 6 `TestMoodJsonUnpacker` tests pass.

- [ ] **Step 3: Commit**

```bash
git add mood_json_nodes.py tests/test_mood_json_nodes.py
git commit -m "feat(unpack): add MoodJsonUnpacker node with tests"
```

---

### Task 3: PromptEnricher — tests

**Files:**
- Modify: `tests/test_mood_json_nodes.py`

- [ ] **Step 1: Append PromptEnricher tests to the test file**

Add this class after `TestMoodJsonUnpacker` in `tests/test_mood_json_nodes.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm PromptEnricher tests fail**

```bash
python -m pytest tests/test_mood_json_nodes.py::TestPromptEnricher -v
```

Expected: `AttributeError: module 'mood_json_nodes' has no attribute 'PromptEnricher'`

---

### Task 4: PromptEnricher — implementation

**Files:**
- Modify: `mood_json_nodes.py`

- [ ] **Step 1: Add PromptEnricher class and update mappings**

Append to `mood_json_nodes.py` (before the `NODE_CLASS_MAPPINGS` dict):

```python
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
            if not value:
                continue
            joined = _join_field(value) if isinstance(value, list) else str(value)
            if not joined:
                continue
            if field == "avoid":
                suffix = f", avoid: {joined}"
            else:
                suffix = f", {joined}"
            result = result + suffix if result else joined
        return (result,)
```

Then update the mapping dicts at the bottom of the file:

```python
NODE_CLASS_MAPPINGS = {
    "MoodJsonUnpacker": MoodJsonUnpacker,
    "PromptEnricher": PromptEnricher,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MoodJsonUnpacker": "Mood JSON Unpacker",
    "PromptEnricher": "Prompt Enricher",
}
```

- [ ] **Step 2: Run all tests**

```bash
python -m pytest tests/test_mood_json_nodes.py -v
```

Expected: all 14 tests pass.

- [ ] **Step 3: Commit**

```bash
git add mood_json_nodes.py tests/test_mood_json_nodes.py
git commit -m "feat(enrich): add PromptEnricher node with tests"
```

---

### Task 5: Wire into ComfyUI + update docs

**Files:**
- Modify: `__init__.py`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update __init__.py to merge both modules**

Replace the entire contents of `__init__.py` with:

```python
from .audio_mood_analyzer import NODE_CLASS_MAPPINGS as _A, NODE_DISPLAY_NAME_MAPPINGS as _DA
from .mood_json_nodes import NODE_CLASS_MAPPINGS as _B, NODE_DISPLAY_NAME_MAPPINGS as _DB

NODE_CLASS_MAPPINGS = {**_A, **_B}
NODE_DISPLAY_NAME_MAPPINGS = {**_DA, **_DB}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

- [ ] **Step 2: Add architecture note to CLAUDE.md**

In `CLAUDE.md`, under the `## Architecture constraints` section, add:

```
- New nodes go in dedicated files (e.g. mood_json_nodes.py); __init__.py merges mappings with {**_A, **_B}.
```

- [ ] **Step 3: Verify full test suite still passes**

```bash
python -m pytest tests/ -q
```

Expected: all existing tests + 14 new tests pass, no failures.

- [ ] **Step 4: Commit**

```bash
git add __init__.py CLAUDE.md
git commit -m "chore: wire mood_json_nodes into ComfyUI; add module architecture note to CLAUDE.md"
```
