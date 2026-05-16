# Design: AnimateDiffScheduleFormatter (T-006)

**Date:** 2026-05-16
**Status:** approved
**Node:** `AnimateDiffScheduleFormatter` (new standalone node, same file/project)
**Depends on:** T-005 — consumes `prompt_sequence_json` output from `AudioMoodAnalyzerTimeline`
**Target:** AnimateDiff Evolved (ADE) prompt travel format

---

## Purpose

Transform the `prompt_sequence_json` output from `AudioMoodAnalyzerTimeline` into a
frame-keyed prompt schedule string consumable by AnimateDiff Evolved's prompt travel
nodes. Each audio segment maps to a frame number derived proportionally from the
segment's start time relative to total audio duration.

---

## Architecture

Standalone node — not a subclass, not an additional output on `AudioMoodAnalyzerTimeline`.
The formatter is a pure string transform: it parses JSON, computes frame numbers, and
formats strings. No Ollama calls. No audio processing.

Placed in `audio_mood_analyzer.py` alongside the other nodes.

---

## Inputs

| Name | Type | Default | Range | Description |
|------|------|---------|-------|-------------|
| `prompt_sequence_json` | STRING | `""` | — | JSON array from `AudioMoodAnalyzerTimeline` |
| `total_frames` | INT | 64 | 8–256 | Must match the AnimateDiff frame count setting |
| `prompt_type` | COMBO | `"merge_prompt"` | `["merge_prompt", "environment_prompt", "subject_prompt"]` | Which prompt field to read from each segment |

---

## Frame number calculation

Segment start times are mapped proportionally to the frame range:

```
total_duration = segments[-1]["end_s"]
frame_i = round(seg["start_s"] / total_duration * total_frames)
frame_i = max(0, min(frame_i, total_frames - 1))   # clamp
```

The first segment always produces frame 0 (start_s = 0.0).
Frame numbers for subsequent segments distribute evenly across [0, total_frames).
No `fps` input — fps is an AnimateDiff-side setting unrelated to the schedule keyframes.

---

## Outputs

| Name | Type | Description |
|------|------|-------------|
| `schedule` | STRING | ADE prompt travel schedule — one `"{frame}": "{prompt}",` line per segment |
| `first_frame_prompt` | STRING | Prompt for frame 0, for wiring into a standard CLIPTextEncode as positive conditioning fallback |

### Output format

```
"0": "dark wasteland, crumbling concrete",
"8": "burning field, ash and smoke",
"16": "flooded ruin, grey water",
```

One line per segment. Trailing comma on every line (ADE prompt travel accepts this).
Lines with empty prompts (Ollama failed for that segment) are **omitted** from the output
rather than emitting a blank keyframe — a blank keyframe in ADE would clear conditioning.

If two segments map to the same frame number (possible when n_segments is large relative
to total_frames), the **later** segment's prompt wins — it overwrites the earlier one for
that frame. This matches natural expectation: the most recent audio segment for a given
frame takes precedence.

---

## Error handling

| Condition | Behaviour |
|-----------|-----------|
| `prompt_sequence_json` is empty string | Return `("", "")` with no error — node is unconnected |
| `prompt_sequence_json` is invalid JSON | Log warning, return `("", "")` |
| `segments` array is empty | Log warning, return `("", "")` |
| Chosen prompt field is `""` for a segment | Skip that segment's keyframe silently |
| All segments have empty chosen prompt | Return `("", "")` |
| `total_frames` ≤ 0 | Treat as 1 (clamping prevents division-related errors) |

---

## Node registration

```python
NODE_CLASS_MAPPINGS = {
    ...
    "AnimateDiffScheduleFormatter": AnimateDiffScheduleFormatter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    ...
    "AnimateDiffScheduleFormatter": "AnimateDiff Schedule Formatter",
}
```

Category: `audio/analysis`

---

## Sample workflow: `example_workflow/example_animatediff.json`

A focused workflow showing the audio → timeline → formatter pipeline. The image-generation
section uses a standard KSampler path (same model stack as other example workflows) with
`first_frame_prompt` wired as positive conditioning — this generates one representative
image from the first segment's prompt and is useful as a sanity check.

**Left section — audio + analysis:**
```
LoadAudio → AudioMoodAnalyzerTimeline (full song, n_segments=8, style_preset=raw)
    ↓
prompt_sequence_json → PreviewAny (inspect full JSON)
    ↓
AnimateDiffScheduleFormatter (total_frames=64, prompt_type=merge_prompt)
    ├─ schedule          → PreviewAny (inspect schedule string for ADE)
    └─ first_frame_prompt → PreviewAny + CLIPTextEncode (positive)
```

**Right section — single-image preview (first segment):**
```
CLIPTextEncode (positive, from first_frame_prompt)
CLIPTextEncode (negative, hardcoded)
KSampler → VAEDecode → SaveImage
```

The `schedule` output PreviewAny node is the primary deliverable of this workflow —
the user inspects the formatted schedule string and pastes/wires it into their ADE
prompt travel node. Full AnimateDiff generation is out of scope for this workflow
because ADE node names and required inputs vary by version.

**Model stack:** same as `example_timeline.json` — zImageTurbo UNET, qwen_3_4b CLIP
(lumina2), ae.safetensors VAE, fear_of_the_art LoRA (disabled).

**`OllamaModelSelector`** included for model discovery (same as `example_timeline.json`).

---

## Out of scope

- AnimateDiff model loading or motion module selection
- Multi-model or per-segment LoRA switching
- Keyframe interpolation curves (linear, ease-in, etc.)
- Deforum or A1111-style schedule formats
- Any changes to existing nodes
