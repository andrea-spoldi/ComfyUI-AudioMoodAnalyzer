# AudioMoodAnalyzerAdvanced — Full Template Override (Option C) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `AudioMoodAnalyzerAdvanced`, a new ComfyUI node that inherits from `AudioMoodAnalyzer` and exposes five optional prompt override fields — one per internal `_build_*` method — so users can replace any built-in template with their own.

**Architecture:** Single new class in `audio_mood_analyzer.py`, inheriting from `AudioMoodAnalyzer`. Overrides `INPUT_TYPES`, `analyze()`, and the five `_build_*` methods. Template variables are substituted via `str.format_map()`; on error the method falls back to `super()`. Both nodes registered in `NODE_CLASS_MAPPINGS`.

**Prerequisite:** Option B (style presets plan) must be fully implemented first. This plan assumes `_build_style_block`, `STYLE_PRESETS`, `style_preset`, and `style_notes` all exist on the base class.

**Tech Stack:** Python 3.x, no new dependencies.

---

## File map

| File | Action |
|------|--------|
| `audio_mood_analyzer.py` | Modify — add `AudioMoodAnalyzerAdvanced` class and update registrations |
| `tests/test_advanced_node.py` | Create — unit tests for override logic and fallback behaviour |

---

### Task 1: Add `AudioMoodAnalyzerAdvanced` class skeleton and registration

**Files:**
- Modify: `audio_mood_analyzer.py`
- Create: `tests/test_advanced_node.py`

- [ ] **Step 1.1: Write failing tests for override detection**

Create `tests/test_advanced_node.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from audio_mood_analyzer import AudioMoodAnalyzerAdvanced, _fmt_json

DUMMY_FEATURES = {"duration_seconds": 30, "tempo_bpm": 120}
DUMMY_MOOD = {"sonic_mood": ["dark"], "energy_profile": "high", "tension_profile": "rising"}
DUMMY_SUBJECT = {"subject_role": "wanderer"}


def test_advanced_node_exists():
    node = AudioMoodAnalyzerAdvanced()
    assert node is not None


def test_input_types_has_override_fields():
    inputs = AudioMoodAnalyzerAdvanced.INPUT_TYPES()
    optional = inputs.get("optional", {})
    assert "mood_prompt_override" in optional
    assert "subject_analysis_prompt_override" in optional
    assert "environment_prompt_override" in optional
    assert "subject_prompt_override" in optional
    assert "merge_prompt_override" in optional


def test_mood_override_used_when_provided():
    node = AudioMoodAnalyzerAdvanced()
    result = node._build_mood_prompt(
        DUMMY_FEATURES, "context",
        mood_prompt_override="custom mood: {features}"
    )
    assert "custom mood:" in result
    assert str(DUMMY_FEATURES["tempo_bpm"]) in result


def test_mood_override_skipped_when_empty():
    node = AudioMoodAnalyzerAdvanced()
    result = node._build_mood_prompt(DUMMY_FEATURES, "context", mood_prompt_override="")
    assert "art director" in result  # built-in template


def test_invalid_override_falls_back_to_builtin():
    node = AudioMoodAnalyzerAdvanced()
    result = node._build_mood_prompt(
        DUMMY_FEATURES, "context",
        mood_prompt_override="bad template: {nonexistent_variable}"
    )
    assert "art director" in result  # fell back
```

- [ ] **Step 1.2: Run tests — expect failure**

```bash
python3 -m pytest tests/test_advanced_node.py -v
```

Expected: `ImportError` — `AudioMoodAnalyzerAdvanced` does not exist yet.

- [ ] **Step 1.3: Add the class skeleton to `audio_mood_analyzer.py`**

Add after the closing `}` of `NODE_DISPLAY_NAME_MAPPINGS` — no, add **before** the `NODE_CLASS_MAPPINGS` lines so the class exists before registration. Insert after the `AudioMoodAnalyzer` class definition (before the mapping dicts):

```python
class AudioMoodAnalyzerAdvanced(AudioMoodAnalyzer):
    """AudioMoodAnalyzer with optional full prompt template overrides."""

    @classmethod
    def INPUT_TYPES(cls):
        base = super().INPUT_TYPES()
        base["optional"] = {
            "mood_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the audio mood analysis prompt. Leave empty to use built-in. "
                    "Available variables: {features}, {custom_context}, {style_block}"
                ),
            }),
            "subject_analysis_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the subject analysis prompt. Leave empty to use built-in. "
                    "Available variables: {lyrics_or_text}, {focus_fragment}, "
                    "{song_title}, {song_description}, {song_genre}, {custom_context}"
                ),
            }),
            "environment_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the environment image-gen prompt. Leave empty to use built-in. "
                    "Available variables: {mood_json}, {subject_json}, {style_block}"
                ),
            }),
            "subject_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the subject image-gen prompt. Leave empty to use built-in. "
                    "Available variables: {subject_json}, {style_block}"
                ),
            }),
            "merge_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the merge prompt. Leave empty to use built-in. "
                    "Available variables: {mood_summary}, {environment_prompt}, "
                    "{subject_prompt}, {style_block}"
                ),
            }),
        }
        return base

    FUNCTION = "analyze"
    CATEGORY = "audio/analysis"
```

- [ ] **Step 1.4: Update `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`**

Replace the two dicts at the bottom of the file:

```python
NODE_CLASS_MAPPINGS = {
    "AudioMoodAnalyzer": AudioMoodAnalyzer,
    "AudioMoodAnalyzerAdvanced": AudioMoodAnalyzerAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioMoodAnalyzer": "Audio Mood Analyzer",
    "AudioMoodAnalyzerAdvanced": "Audio Mood Analyzer (Advanced)",
}
```

- [ ] **Step 1.5: Run tests — expect partial pass**

```bash
python3 -m pytest tests/test_advanced_node.py::test_advanced_node_exists tests/test_advanced_node.py::test_input_types_has_override_fields -v
```

Expected: both `PASSED`. The override-logic tests will still fail.

- [ ] **Step 1.6: Commit**

```bash
git add audio_mood_analyzer.py tests/test_advanced_node.py
git commit -m "feat: add AudioMoodAnalyzerAdvanced skeleton with optional override inputs"
```

---

### Task 2: Override the five `_build_*` methods with fallback logic

**Files:**
- Modify: `audio_mood_analyzer.py`

- [ ] **Step 2.1: Add a shared `_render_override` helper to `AudioMoodAnalyzerAdvanced`**

Add this method to the class before any `_build_*` overrides:

```python
def _render_override(self, template: str, context: dict, label: str) -> str | None:
    """Return rendered template string, or None if template is empty or rendering fails."""
    if not template.strip():
        return None
    try:
        return template.format_map(context)
    except (KeyError, ValueError) as exc:
        print(f"{_LOG} ⚠ {label} override render failed ({exc}); using built-in template")
        return None
```

- [ ] **Step 2.2: Override `_build_mood_prompt`**

```python
def _build_mood_prompt(self, features, custom_context, mood_prompt_override="", **kwargs):
    rendered = self._render_override(
        mood_prompt_override,
        {
            "features": _fmt_json(features),
            "custom_context": custom_context,
            "style_block": kwargs.get("style_block", ""),
        },
        "mood_prompt",
    )
    return rendered if rendered is not None else super()._build_mood_prompt(features, custom_context)
```

- [ ] **Step 2.3: Override `_build_subject_analysis_prompt`**

```python
def _build_subject_analysis_prompt(
    self,
    lyrics_or_text,
    focus_fragment,
    song_title,
    custom_context,
    song_description="",
    song_genre="",
    subject_analysis_prompt_override="",
):
    rendered = self._render_override(
        subject_analysis_prompt_override,
        {
            "lyrics_or_text": lyrics_or_text,
            "focus_fragment": focus_fragment,
            "song_title": song_title,
            "song_description": song_description,
            "song_genre": song_genre,
            "custom_context": custom_context,
        },
        "subject_analysis_prompt",
    )
    return rendered if rendered is not None else super()._build_subject_analysis_prompt(
        lyrics_or_text=lyrics_or_text,
        focus_fragment=focus_fragment,
        song_title=song_title,
        custom_context=custom_context,
        song_description=song_description,
        song_genre=song_genre,
    )
```

- [ ] **Step 2.4: Override `_build_environment_prompt_request`**

```python
def _build_environment_prompt_request(
    self, mood_json, subject_json, style_block, environment_prompt_override=""
):
    rendered = self._render_override(
        environment_prompt_override,
        {
            "mood_json": _fmt_json(mood_json),
            "subject_json": _fmt_json(subject_json),
            "style_block": style_block,
        },
        "environment_prompt",
    )
    return rendered if rendered is not None else super()._build_environment_prompt_request(
        mood_json=mood_json,
        subject_json=subject_json,
        style_block=style_block,
    )
```

- [ ] **Step 2.5: Override `_build_subject_prompt_request`**

```python
def _build_subject_prompt_request(self, subject_json, style_block, subject_prompt_override=""):
    rendered = self._render_override(
        subject_prompt_override,
        {
            "subject_json": _fmt_json(subject_json),
            "style_block": style_block,
        },
        "subject_prompt",
    )
    return rendered if rendered is not None else super()._build_subject_prompt_request(
        subject_json=subject_json,
        style_block=style_block,
    )
```

- [ ] **Step 2.6: Override `_build_merge_prompt_request`**

```python
def _build_merge_prompt_request(
    self,
    mood_summary,
    environment_prompt,
    subject_prompt,
    style_block,
    merge_prompt_override="",
):
    rendered = self._render_override(
        merge_prompt_override,
        {
            "mood_summary": mood_summary,
            "environment_prompt": environment_prompt,
            "subject_prompt": subject_prompt,
            "style_block": style_block,
        },
        "merge_prompt",
    )
    return rendered if rendered is not None else super()._build_merge_prompt_request(
        mood_summary=mood_summary,
        environment_prompt=environment_prompt,
        subject_prompt=subject_prompt,
        style_block=style_block,
    )
```

- [ ] **Step 2.7: Run override tests — expect pass**

```bash
python3 -m pytest tests/test_advanced_node.py -v
```

Expected: all 5 tests `PASSED`.

- [ ] **Step 2.8: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat: implement override logic for all five _build_* methods in AudioMoodAnalyzerAdvanced"
```

---

### Task 3: Override `analyze()` to pass override strings to builders

`AudioMoodAnalyzerAdvanced.analyze()` must accept the five override parameters from ComfyUI and forward each one to the corresponding `_build_*` call.

**Files:**
- Modify: `audio_mood_analyzer.py`
- Modify: `tests/test_advanced_node.py`

- [ ] **Step 3.1: Add an integration test for analyze() with override (mocked Ollama)**

Add to `tests/test_advanced_node.py`:

```python
from unittest.mock import patch

def test_analyze_passes_override_to_mood_builder():
    """Verify that mood_prompt_override reaches _build_mood_prompt in analyze()."""
    node = AudioMoodAnalyzerAdvanced()
    with patch.object(node, '_build_mood_prompt', wraps=node._build_mood_prompt) as mock_build, \
         patch.object(node, '_timed_generate', return_value='{"sonic_mood":[],"energy_profile":"","tension_profile":"","visual_environment_implications":[],"lighting_implications":[],"color_palette":[],"texture_implications":[],"subject_presence":[],"composition_suggestions":[],"motion_feel":[],"camera_language":[],"avoid":[]}'), \
         patch.object(node, '_audio_to_numpy', return_value=([], 44100)), \
         patch.object(node, '_extract_features', return_value=DUMMY_FEATURES):
        try:
            node.analyze(
                audio={},
                ollama_url="http://localhost:11434/api/generate",
                model="test",
                analysis_temperature=0.4,
                prompt_temperature=0.8,
                custom_context="ctx",
                lyrics_or_text="",
                focus_fragment="",
                song_title="",
                song_description="",
                song_genre="",
                style_preset="painterly",
                style_notes="",
                generate_environment_prompt=False,
                generate_subject_prompt=False,
                generate_merge_prompt=False,
                mood_prompt_override="override: {features}",
                subject_analysis_prompt_override="",
                environment_prompt_override="",
                subject_prompt_override="",
                merge_prompt_override="",
            )
        except Exception:
            pass  # Ollama not available; we only care about the call below
        mock_build.assert_called_once()
        _, kwargs = mock_build.call_args
        assert kwargs.get("mood_prompt_override") == "override: {features}"
```

- [ ] **Step 3.2: Run test — expect failure**

```bash
python3 -m pytest tests/test_advanced_node.py::test_analyze_passes_override_to_mood_builder -v
```

Expected: `FAILED` — `analyze()` does not yet accept override params.

- [ ] **Step 3.3: Add `analyze()` override to `AudioMoodAnalyzerAdvanced`**

```python
def analyze(
    self,
    audio,
    ollama_url,
    model,
    analysis_temperature,
    prompt_temperature,
    custom_context,
    lyrics_or_text,
    focus_fragment,
    song_title,
    song_description,
    song_genre,
    style_preset,
    style_notes,
    generate_environment_prompt,
    generate_subject_prompt,
    generate_merge_prompt,
    mood_prompt_override="",
    subject_analysis_prompt_override="",
    environment_prompt_override="",
    subject_prompt_override="",
    merge_prompt_override="",
):
    self._mood_prompt_override = mood_prompt_override
    self._subject_analysis_prompt_override = subject_analysis_prompt_override
    self._environment_prompt_override = environment_prompt_override
    self._subject_prompt_override = subject_prompt_override
    self._merge_prompt_override = merge_prompt_override
    return super().analyze(
        audio=audio,
        ollama_url=ollama_url,
        model=model,
        analysis_temperature=analysis_temperature,
        prompt_temperature=prompt_temperature,
        custom_context=custom_context,
        lyrics_or_text=lyrics_or_text,
        focus_fragment=focus_fragment,
        song_title=song_title,
        song_description=song_description,
        song_genre=song_genre,
        style_preset=style_preset,
        style_notes=style_notes,
        generate_environment_prompt=generate_environment_prompt,
        generate_subject_prompt=generate_subject_prompt,
        generate_merge_prompt=generate_merge_prompt,
    )
```

Then update the five `_build_*` override methods to read from `self._*_override` instance attributes instead of method kwargs:

```python
def _build_mood_prompt(self, features, custom_context):
    rendered = self._render_override(
        getattr(self, "_mood_prompt_override", ""),
        {
            "features": _fmt_json(features),
            "custom_context": custom_context,
            "style_block": getattr(self, "_style_block", ""),
        },
        "mood_prompt",
    )
    return rendered if rendered is not None else super()._build_mood_prompt(features, custom_context)
```

Apply the same `getattr(self, "_*_override", "")` pattern to the other four methods. Also store `style_block` on `self` in `analyze()` before calling `super()`:

```python
self._style_block = _build_style_block(style_preset, style_notes)
```

Add this line in `analyze()` right before `self._mood_prompt_override = ...`.

- [ ] **Step 3.4: Run all tests**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests `PASSED`.

- [ ] **Step 3.5: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3.6: Final commit**

```bash
git add audio_mood_analyzer.py tests/test_advanced_node.py
git commit -m "feat: AudioMoodAnalyzerAdvanced.analyze() wires override strings to _build_* methods"
```

---

## Self-review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| New class inheriting from AudioMoodAnalyzer | Task 1.3 |
| 5 optional override fields in INPUT_TYPES optional group | Task 1.3 |
| Tooltip documents available variables per field | Task 1.3 |
| Override used when non-empty | Tasks 2.2–2.6 |
| Falls back to super() when override empty | Tasks 2.2–2.6 |
| Falls back to super() on KeyError/ValueError | Task 2.1 (_render_override) |
| Logs warning on render failure | Task 2.1 (_render_override) |
| Template variables substituted via format_map | Task 2.1 (_render_override) |
| analyze() accepts 5 override params | Task 3.3 |
| Both nodes registered in NODE_CLASS_MAPPINGS | Task 1.4 |
| "Audio Mood Analyzer (Advanced)" display name | Task 1.4 |
| audio/analysis category | Task 1.3 |
| Infrastructure not overridable (audio extraction, Ollama, JSON parsing) | N/A — not touched |

All spec requirements covered. No placeholders. Type names consistent throughout.
