# Design — Composition Inference Node

**Date:** 2026-05-19
**Status:** Approved

---

## Goal

Infer visual composition metadata from semantic and sonic analysis, and expose it as:
- a structured `composition_json` for downstream logic
- `width` / `height` INT outputs for direct wiring to Empty Latent Image in ComfyUI
- a `composition_prompt` STRING as a new prompt layer alongside environment/subject

---

## Node Shape

**Name:** `CompositionInferenceNode`
**Category:** `audio/analysis`
**File:** `audio_mood_analyzer.py` (single-file constraint)

### Inputs

| Name | Type | Default |
|---|---|---|
| `mood_json` | STRING | — |
| `subject_json` | STRING | — |
| `ollama_url` | STRING | `http://localhost:11434/api/generate` |
| `model` | STRING | `qwen3:14b` |
| `analysis_temperature` | FLOAT | 0.4 |
| `prompt_temperature` | FLOAT | 0.8 |

### Outputs

| Name | Type | Purpose |
|---|---|---|
| `composition_json` | STRING | Full structured JSON |
| `composition_prompt` | STRING | Prose prompt layer (placement, camera, framing) |
| `width` | INT | Parsed from `recommended_resolution` |
| `height` | INT | Parsed from `recommended_resolution` |

---

## Call Sequence

1. **Call 1** (`analysis_temperature`) — LLM infers `composition_json` from `mood_json` + `subject_json`
2. Parse `recommended_resolution` string → `width`, `height`
3. **Call 2** (`prompt_temperature`) — LLM generates prose `composition_prompt` from `composition_json`

Composition is semantically driven: `subject_json` (extracted from lyrics/focus fragments/description) is the primary signal; `mood_json` provides sonic atmosphere as supporting context.

---

## `composition_json` Schema

```json
{
  "aspect_ratio": {
    "orientation": "portrait",
    "ratio": "4:5",
    "recommended_resolution": "1024x1280"
  },
  "subject_placement": {
    "position": "lower_right",
    "size_weight": 0.35
  },
  "environment": {
    "weight": 0.65,
    "negative_space": "high"
  },
  "camera": {
    "distance": "medium",
    "framing_style": "environment_dominant",
    "crop": "waist_up"
  }
}
```

### Allowed Values

| Field | Values |
|---|---|
| `orientation` | `portrait` \| `landscape` \| `square` |
| `ratio` | `4:5` \| `16:9` \| `9:16` \| `1:1` \| `3:2` \| `2:3` |
| `recommended_resolution` | see resolution table below |
| `position` | `center` \| `lower_left` \| `lower_right` \| `upper_left` \| `upper_right` \| `off_frame` |
| `negative_space` | `low` \| `medium` \| `high` |
| `distance` | `close` \| `medium` \| `wide` |
| `framing_style` | `subject_dominant` \| `environment_dominant` \| `balanced` |
| `crop` | `full_body` \| `waist_up` \| `bust` \| `face_only` \| `none` |

### Resolution Table

| Ratio | Portrait | Landscape |
|---|---|---|
| 4:5 / 5:4 | 1024×1280 | 1280×1024 |
| 9:16 | 768×1344 | 1344×768 |
| 16:9 | 896×1152 | 1152×896 |
| 1:1 | 1024×1024 | 1024×1024 |
| 2:3 | 832×1216 | 1216×832 |
| 3:2 | 1216×832 | 832×1216 |

`width`/`height` parsed by splitting `recommended_resolution` on `×` or `x` and casting to int.

---

## Error Handling

**Empty/missing `subject_json`:** Node runs; LLM infers from `mood_json` alone and defaults toward `environment_dominant` + `crop: "none"`. No error raised, console warning logged.

**Malformed Call 1 response:** Falls back to safe defaults and logs a warning:
```json
{
  "aspect_ratio": {"orientation": "square", "ratio": "1:1", "recommended_resolution": "1024x1024"},
  "subject_placement": {"position": "center", "size_weight": 0.5},
  "environment": {"weight": 0.5, "negative_space": "medium"},
  "camera": {"distance": "medium", "framing_style": "balanced", "crop": "none"}
}
```
→ `width=1024`, `height=1024`

**Empty Call 2 response:** `composition_prompt` returns `""` with a console warning. Same pattern as other prompt generation failures.

**Resolution parse failure:** Default to `1024×1024`.

---

## Testing

Tests are scoped to a separate backlog task (T-009) to avoid token burn during implementation. Coverage targets:
- All required keys present in `composition_json`
- `orientation` constrained to allowed values
- `width` / `height` are positive integers matching `recommended_resolution`
- `composition_prompt` is non-empty string
- Fallback to `1024×1024` on malformed LLM response
- Empty `subject_json` does not raise

---

## ADR — Approach Selection

### Chosen: A — Two-call pipeline

Call 1 at `analysis_temperature` produces structured `composition_json`; Call 2 at `prompt_temperature` produces prose `composition_prompt`. Matches the existing analysis/generation temperature separation used throughout the codebase.

### Rejected: B — Single call, JSON includes prompt field

One LLM call returns both structured data and a `composition_prompt` field inside the JSON. Simpler and fewer Ollama calls, but conflates structured inference with creative prose generation — temperature cannot be tuned independently, and mixing free text inside a strict JSON schema is fragile.

### Rejected: C — Single call + template-based prompt

One LLM call returns `composition_json`; `composition_prompt` is assembled programmatically from the JSON fields. Fast and deterministic, but produces mechanical prompt strings ("lower_right placement, waist_up crop") rather than the natural art-direction prose that characterises the other prompt outputs.
