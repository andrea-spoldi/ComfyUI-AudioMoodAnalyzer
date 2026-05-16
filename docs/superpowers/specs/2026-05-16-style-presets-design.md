# Design: Style Presets + Prompt Refinement (Option B)

**Date:** 2026-05-16
**Status:** approved
**Node:** `AudioMoodAnalyzer` (existing node, enhanced)

---

## Problem

The node's five prompt-building methods treat two fundamentally different
pipeline phases as identical. Analysis prompts (produce structured JSON) need
objectivity and tight structure. Generation prompts (produce image-gen text)
need aesthetic personality and style direction. Both currently receive the
same `custom_context` field, which creates friction in both directions: a
style note like "cinematic noir" biases the JSON analysis; a neutral analysis
instruction adds nothing to the creative output.

There are also four structural bugs that degrade output quality silently.

---

## Pipeline phases

### Phase 1 — Analysis (low temp, JSON output)
- `_build_mood_prompt`: raw audio feature dict → mood JSON
- `_build_subject_analysis_prompt`: lyrics + metadata → subject JSON

### Phase 2 — Generation (high temp, creative text output)
- `_build_environment_prompt_request`: JSONs → environment image prompt
- `_build_subject_prompt_request`: subject JSON → portrait prompt
- `_build_merge_prompt_request`: both → final merged prompt

---

## Structural bugs to fix

| # | Location | Bug | Fix |
|---|----------|-----|-----|
| 1 | `_build_environment_prompt_request` | 4-space leading indent on every prompt line (f-string indentation artifact) | Restructure f-string to start at column 0 |
| 2 | `_build_subject_analysis_prompt` | Same indentation issue | Same fix |
| 3 | `_build_subject_analysis_prompt` | `song_title` always printed even when blank (unlike `song_description`/`song_genre` which are conditionally injected) | Apply same conditional pattern |
| 4 | `_build_merge_prompt_request` | Receives empty `subject_prompt` string when no lyrics provided; still asks model to "merge" it, degrading output | Detect empty subject; switch to "refine and elevate" framing when subject is absent |

Additionally: move the "Return only valid JSON" instruction to be the **final sentence** in both analysis prompts. Thinking models (qwen3) sometimes output text after the JSON; placing the instruction last reduces this.

---

## New inputs

### `style_preset` — ComfyUI dropdown

```python
"style_preset": (["painterly", "cinematic", "raw", "abstract", "custom"], {
    "default": "painterly"
})
```

Controls the aesthetic anchor injected into the three **generation prompts only**.
Has no effect on analysis prompts.

### `style_notes` — optional free text

```python
"style_notes": ("STRING", {
    "multiline": True,
    "default": ""
})
```

Appended to the active preset. When `style_preset` is `"custom"`, this field
is used alone (the preset contributes nothing).

### Composition rules

| preset | style_notes | Result injected into generation prompts |
|--------|-------------|----------------------------------------|
| painterly | (empty) | preset definition only |
| painterly | "cold palette, early morning light" | preset + "\n" + style_notes |
| custom | "my custom direction" | style_notes only |
| custom | (empty) | empty string (no style anchor) |

---

## Preset definitions

```python
STYLE_PRESETS = {
    "painterly": (
        "Target aesthetic: oil painting, raw expressive brushwork, emotionally loaded colour, "
        "controlled distortion. Reference painters: Francis Bacon, Egon Schiele, Lucian Freud. "
        "Avoid photorealism, digital gloss, and smooth gradients."
    ),
    "cinematic": (
        "Target aesthetic: wide cinematic frame, dramatic directional lighting, atmospheric haze, "
        "filmic grain and restrained desaturation. Reference directors: Tarkovsky, Wong Kar-wai, "
        "Villeneuve. Avoid flat lighting, TV aesthetics, and oversaturated colour."
    ),
    "raw": (
        "Target aesthetic: immediate, visceral, lo-fi. Grainy, desaturated, imperfect, "
        "documentary-adjacent. No production value. Avoid polish, glamour, and beauty lighting."
    ),
    "abstract": (
        "Target aesthetic: non-representational, gestural abstraction, colour field, "
        "mark-making as pure emotion. Reference: Rothko, Kiefer, Twombly. "
        "Avoid literal depiction of subjects or recognisable scenes."
    ),
    "custom": "",
}
```

---

## Style block injection

A `_build_style_block(style_preset, style_notes)` helper builds the final
style string. It is called once in `analyze()` and passed to all three
generation prompt builders.

Generation prompts receive it as a dedicated section when non-empty:

```
Visual style target:
{style_block}
```

Placed after the role description and before the focus instructions, so the
model has the aesthetic constraint before reading the data. When `style_block`
is empty (preset `"custom"` with empty `style_notes`), the section is omitted
entirely — no empty heading is sent to the model.

---

## `custom_context` — scope clarified

The existing `custom_context` field is kept unchanged (parameter name, position,
default value) for backwards compatibility. Its role is now explicitly
**analysis context only**: it is injected into the two analysis prompts and
removed from the three generation prompts, which use the style block instead.

The default value is updated to reflect this:
> "Analyze the music as pure sound, not lyrics. Translate sonic qualities into emotional visual direction."

This is already accurate for analysis; the change is removal from generation prompts.

---

## Prompt changes summary

| Prompt | Changes |
|--------|---------|
| `_build_mood_prompt` | Fix indentation; move JSON-only instruction to final line |
| `_build_subject_analysis_prompt` | Fix indentation; conditional song_title; move JSON-only to final line |
| `_build_environment_prompt_request` | Fix indentation; remove custom_context; inject style_block |
| `_build_subject_prompt_request` | Remove custom_context; inject style_block |
| `_build_merge_prompt_request` | Remove custom_context; inject style_block; use `summary` instead of full mood_json; handle empty subject_prompt |

---

## `analyze()` signature delta

Added parameters (inserted after `song_genre`, before `generate_*` booleans):
```python
style_preset,   # str, default "painterly"
style_notes,    # str, default ""
```

---

## Out of scope

- No changes to audio feature extraction
- No changes to Ollama connection logic
- No changes to return types or output names
- Option C (advanced template overrides) is a separate spec
