# Design: AudioMoodAnalyzerAdvanced — Full Template Override (Option C)

**Date:** 2026-05-16
**Status:** approved
**Node:** `AudioMoodAnalyzerAdvanced` (new node, same file/project)
**Depends on:** Option B spec — this node builds on top of the improved base node

---

## Purpose

A power-user variant of `AudioMoodAnalyzer` that exposes the five
internal prompt templates as editable inputs. When an override field is
non-empty, it replaces the built-in template entirely. When empty, the
built-in template (post Option B improvements) is used.

The base node remains the primary user-facing node. The Advanced node
targets users who want to write their own prompts or experiment with
fundamentally different analytic or aesthetic approaches.

---

## Architecture

`AudioMoodAnalyzerAdvanced` **inherits from `AudioMoodAnalyzer`**.

```
AudioMoodAnalyzer
    ↑
AudioMoodAnalyzerAdvanced
```

It overrides:
- `INPUT_TYPES` — adds 5 optional template override fields
- `analyze()` — accepts the 5 override strings and passes each to the corresponding builder
- Five `_build_*` methods — each accepts an optional override kwarg; uses it when non-empty, otherwise calls `super()`

No logic is duplicated. The parent node's audio extraction, feature
computation, Ollama calls, JSON parsing, and summary generation are all
inherited unchanged.

---

## New inputs (added on top of all base node inputs)

Five optional multiline STRING fields, one per prompt-building method.
Default value for each is an empty string, meaning "use built-in template".

```python
"mood_prompt_override": ("STRING", {
    "multiline": True,
    "default": "",
    "tooltip": "Override the audio mood analysis prompt. Leave empty to use built-in."
}),
"subject_analysis_prompt_override": ("STRING", {
    "multiline": True,
    "default": "",
    "tooltip": "Override the subject analysis prompt. Leave empty to use built-in."
}),
"environment_prompt_override": ("STRING", {
    "multiline": True,
    "default": "",
    "tooltip": "Override the environment image-gen prompt. Leave empty to use built-in."
}),
"subject_prompt_override": ("STRING", {
    "multiline": True,
    "default": "",
    "tooltip": "Override the subject image-gen prompt. Leave empty to use built-in."
}),
"merge_prompt_override": ("STRING", {
    "multiline": True,
    "default": "",
    "tooltip": "Override the merge prompt. Leave empty to use built-in."
}),
```

These are added in an `"optional"` group in `INPUT_TYPES` so they appear
collapsed by default in the ComfyUI node UI.

---

## Template variable substitution

When an override template is non-empty, it is rendered via Python
`str.format_map()` with a context dict populated from available data at
call time. The user writes `{variable_name}` placeholders in their template.

### Available variables per prompt

| Prompt | Available variables |
|--------|-------------------|
| mood | `{features}`, `{custom_context}`, `{style_block}` |
| subject analysis | `{lyrics_or_text}`, `{focus_fragment}`, `{song_title}`, `{song_description}`, `{song_genre}`, `{custom_context}` |
| environment | `{mood_json}`, `{subject_json}`, `{style_block}` |
| subject | `{subject_json}`, `{style_block}` |
| merge | `{mood_summary}`, `{environment_prompt}`, `{subject_prompt}`, `{style_block}` |

`{style_block}` is the same style preset string from Option B.
`{mood_summary}` is the compact summary string, not the full JSON.

Variables are documented in the default tooltip/placeholder text of each
override field so the user can discover them without reading source code.

### Error handling

If `str.format_map()` raises `KeyError` (unknown variable) or
`ValueError` (bad format string), the node logs a warning and falls back
to the built-in template for that prompt. It does not crash the entire run.

---

## Override logic per method

```python
# Pattern applied to each of the five methods:
def _build_mood_prompt(self, features, custom_context, mood_prompt_override="", **kwargs):
    if mood_prompt_override.strip():
        try:
            return mood_prompt_override.format_map({
                "features": _fmt_json(features),
                "custom_context": custom_context,
                "style_block": kwargs.get("style_block", ""),
            })
        except (KeyError, ValueError) as e:
            print(f"{_LOG} ⚠ mood_prompt_override render failed ({e}); using built-in")
    return super()._build_mood_prompt(features, custom_context)
```

---

## Node registration

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

Both nodes appear under the `audio/analysis` category.

---

## What is NOT overridable

- Audio feature extraction (`_extract_features`, `_section_energy`)
- Ollama connection and retry logic (`_ollama_generate`, `_timed_generate`)
- JSON parsing (`_extract_json`)
- Return types and output names

These are infrastructure, not prompts. Overriding them would require a
different node entirely.

---

## Out of scope

- No preset system changes (inherited from Option B)
- No new output pins
- No UI beyond the five override fields
- No prompt versioning or history
