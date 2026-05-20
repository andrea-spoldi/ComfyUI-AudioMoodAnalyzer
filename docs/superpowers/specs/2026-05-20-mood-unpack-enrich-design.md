# Design: MoodJsonUnpacker + PromptEnricher

**Date:** 2026-05-20
**Status:** Approved

## Problem

`AudioMoodAnalyzer` produces a rich `mood_json` with 11 fields (color palettes, lighting
implications, texture suggestions, composition cues, etc.) but exposes them only as a
single opaque STRING. Users cannot wire individual fields to CLIPTextEncode or other nodes,
and the structured analysis data does not visibly shape the final prompts.

## Goal

1. **(B)** Make individual mood_json fields accessible as ComfyUI outputs.
2. **(C)** Allow any prompt to be deterministically enriched with selected mood fields — no
   extra LLM call.

## File Structure

New file: `mood_json_nodes.py` (same directory as `audio_mood_analyzer.py`).
Start flat — a `nodes/` subdirectory is premature until 3+ modules exist.

`__init__.py` merges both mapping dicts:

```python
from .audio_mood_analyzer import NODE_CLASS_MAPPINGS as _A, NODE_DISPLAY_NAME_MAPPINGS as _DA
from .mood_json_nodes import NODE_CLASS_MAPPINGS as _B, NODE_DISPLAY_NAME_MAPPINGS as _DB

NODE_CLASS_MAPPINGS = {**_A, **_B}
NODE_DISPLAY_NAME_MAPPINGS = {**_DA, **_DB}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

## Node 1: MoodJsonUnpacker

**Category:** `audio/mood`

### Input

| Name | Type | Notes |
|------|------|-------|
| `mood_json` | STRING | Raw JSON string from AudioMoodAnalyzer |

### Outputs (8 STRINGs)

| Name | Source field | Array handling |
|------|-------------|----------------|
| `sonic_mood` | `sonic_mood` | joined with `, ` |
| `energy_profile` | `energy_profile` | string as-is |
| `tension_profile` | `tension_profile` | string as-is |
| `color_palette` | `color_palette` | joined with `, ` |
| `lighting_implications` | `lighting_implications` | joined with `, ` |
| `texture_implications` | `texture_implications` | joined with `, ` |
| `composition_suggestions` | `composition_suggestions` | joined with `, ` |
| `avoid` | `avoid` | joined with `, ` |

### Behaviour

- Parses `mood_json` with `json.loads`. On `JSONDecodeError` or if input is empty: all
  outputs return `""` (never raises).
- Missing keys → `""` (never raises).
- Lists → comma-joined string. Non-list values → `str()`.

### Not included

`visual_environment_implications`, `subject_presence`, `motion_feel`, `camera_language`
are present in mood_json but left out of outputs to keep the node focused. They can be
added later if needed.

## Node 2: PromptEnricher

**Category:** `audio/mood`

### Inputs

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `prompt` | STRING | `""` | Base prompt to enrich |
| `mood_json` | STRING | `""` | Raw JSON string from AudioMoodAnalyzer |
| `fields_to_inject` | STRING (multiline) | `color_palette\nlighting_implications\ntexture_implications` | One field name per line |

### Output

| Name | Type |
|------|------|
| `enriched_prompt` | STRING |

### Behaviour

- Parse `mood_json`. On failure: return `prompt` unchanged.
- Parse `fields_to_inject`: split on newlines, strip whitespace, skip blank lines.
- For each field name:
  - Look up in parsed JSON. If missing or empty: skip silently.
  - If value is a list: join with `, `.
  - If field name is `avoid`: prefix the joined value with `avoid: `.
  - Otherwise: append `, <value>` to the growing prompt string.
- Return final enriched string.
- Empty `prompt` input is valid — enriched output is the injected fields only.

### Injection order

Fields are appended in the order listed in `fields_to_inject`, not by JSON key order.

## CLAUDE.md update

Add one line to the "Architecture constraints" section:

```
- New nodes go in dedicated files (e.g. mood_json_nodes.py); __init__.py merges mappings.
```

## Testing

### MoodJsonUnpacker

- Valid mood_json → all 8 outputs correct
- List fields joined correctly with `, `
- Missing key → `""` (no KeyError)
- Malformed JSON → all outputs `""`
- Empty string input → all outputs `""`

### PromptEnricher

- Default fields injected onto a base prompt
- `avoid` field prefixed with `avoid: `
- Unknown field name in `fields_to_inject` → silently skipped
- Malformed `mood_json` → returns `prompt` unchanged
- Empty `prompt` → returns injected fields only
- Empty `fields_to_inject` → returns `prompt` unchanged
- Field present but empty list → skipped
