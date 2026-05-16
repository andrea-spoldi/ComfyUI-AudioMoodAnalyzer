# Design: AudioMoodAnalyzerTimeline (T-005)

**Date:** 2026-05-16
**Status:** approved
**Node:** `AudioMoodAnalyzerTimeline` (new node, same file/project)
**Depends on:** Option B (style presets) — assumes `_build_style_block`, `STYLE_PRESETS`, and all `_build_*` prompt methods exist on `AudioMoodAnalyzer`.

---

## Purpose

Generate a time-indexed sequence of image-generation prompts from a single audio input by dividing the audio into N equal segments and running the full analysis + generation pipeline on each. Designed for image sequence and video generation workflows where each frame (or group of frames) should reflect the sonic character of its corresponding audio moment.

---

## Architecture

`AudioMoodAnalyzerTimeline` **inherits from `AudioMoodAnalyzer`**.

```
AudioMoodAnalyzer
    ↑
AudioMoodAnalyzerTimeline
```

It overrides:
- `INPUT_TYPES` — adds `n_segments` INT input
- `RETURN_TYPES` / `RETURN_NAMES` / `FUNCTION` — replaces parent's 6-output signature with 4 timeline outputs
- `analyze_timeline()` — new method; does NOT call `super().analyze()`

All `_build_*` prompt methods are inherited unchanged. Audio extraction and Ollama infrastructure are inherited unchanged.

---

## Segmentation

Audio is divided into `n_segments` **equal-duration slices** by sample count:

```
segment_samples = total_samples // n_segments
segment i: y[i * segment_samples : (i+1) * segment_samples]
last segment: y[(n_segments-1) * segment_samples :]  # absorbs any remainder
```

Each slice is passed to `_extract_features(y_seg, sr)` independently.

Beat-aligned segmentation is out of scope for this version.

---

## Pipeline per run

### Subject analysis — once

If any of `lyrics_or_text`, `focus_fragment`, `song_title`, `song_description`, `song_genre` is non-empty:
- Run `_build_subject_analysis_prompt(...)` → Ollama → `subject_json`
- Run `_build_subject_prompt_request(subject_json, style_block)` → Ollama → `subject_prompt_str`

Otherwise both are empty. Subject prompt is **shared across all segments** — it describes the same figure throughout the sequence.

### Per segment (×N)

For each segment `i`:
1. Extract features from the audio slice → `features`
2. Mood analysis: `_build_mood_prompt(features, custom_context)` → Ollama → `mood_json`
3. Build `mood_summary = _build_summary(mood_json)`
4. Environment prompt: `_build_environment_prompt_request(mood_json, subject_json, style_block)` → Ollama
5. Merge prompt: `_build_merge_prompt_request(mood_summary, environment_prompt, subject_prompt_str, style_block)` → Ollama

**Calls per run:** N×3 + (0 or 2) subject calls. At N=8: 24–26 Ollama calls.

### Error handling per segment

If any individual Ollama call fails or returns empty, the corresponding field is set to `""` and a warning is logged. The run continues — partial results are preserved. The node never aborts mid-sequence.

---

## New input

`n_segments` (INT, default 8, min 2, max 32) — inserted into `INPUT_TYPES["required"]` after `style_notes` and before `generate_environment_prompt`.

All parent inputs are inherited: `audio`, `ollama_url`, `model`, `analysis_temperature`, `prompt_temperature`, `custom_context`, `lyrics_or_text`, `focus_fragment`, `song_title`, `song_description`, `song_genre`, `style_preset`, `style_notes`, `generate_environment_prompt`, `generate_subject_prompt`, `generate_merge_prompt`.

The `generate_*` booleans from the parent are honored: setting `generate_environment_prompt=False` skips environment prompt calls for all segments; same for subject and merge.

---

## Outputs

| Name | Type | Content |
|------|------|---------|
| `prompt_sequence_json` | STRING | JSON array — one object per segment (see schema below) |
| `merge_prompts` | STRING | Merge prompts only, newline-separated, one per segment |
| `environment_prompts` | STRING | Environment prompts only, newline-separated, one per segment |
| `subject_prompt` | STRING | Single shared subject prompt (empty string if no subject data provided or `generate_subject_prompt=False`) |

### `prompt_sequence_json` schema

```json
[
  {
    "segment": 1,
    "start_s": 0.0,
    "end_s": 4.5,
    "mood_json": { ... },
    "environment_prompt": "...",
    "subject_prompt": "...",
    "merge_prompt": "..."
  },
  ...
]
```

`subject_prompt` is repeated on each segment object (same value in all) for consumer convenience — AnimateDiff formatter (T-006) and other downstream nodes can read a single object without needing to look elsewhere.

---

## Node registration

```python
NODE_CLASS_MAPPINGS = {
    ...
    "AudioMoodAnalyzerTimeline": AudioMoodAnalyzerTimeline,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    ...
    "AudioMoodAnalyzerTimeline": "Audio Mood Analyzer (Timeline)",
}
```

Category: `audio/analysis`.

---

## Sample workflow: `example_workflow/example_timeline.json`

A new workflow file demonstrating the timeline node. Uses the same model stack as `example.json` (zImageTurbo UNET, qwen_3_4b CLIP/lumina2, ae.safetensors VAE, fear_of_the_art LoRA).

**Left side — audio + timeline analysis:**
- `LoadAudio` → `FL_Audio_Crop` (0:39–0:57, same Jeremy clip)
- `PreviewAudio` for the cropped segment
- `OllamaModelSelector` → `AudioMoodAnalyzerTimeline.model`
- `AudioMoodAnalyzerTimeline` (n_segments=8, style_preset=raw, Jeremy metadata)
- `PreviewAny` nodes for all 4 outputs (prompt_sequence_json, merge_prompts, environment_prompts, subject_prompt)

**Right side — single-image sanity check:**
- `merge_prompts` → `CLIPTextEncode` (positive) → `KSampler` → `VAEDecode` → `SaveImage`
- `CLIPTextEncode` (negative, same hardcoded negative as example.json)
- `ConditioningAverage` is not used here — single encoding of the full merge_prompts string as a quick preview

The workflow does not produce a full image sequence (that requires T-006). Its purpose is to verify the timeline node output is correct and to show what the combined prompts look like when fed into image generation.

---

## Out of scope

- Beat-aligned segmentation
- Per-segment LoRA or model switching
- Dynamic n_segments from audio duration
- Full image sequence batch generation (covered by T-006)
- Any changes to existing nodes
