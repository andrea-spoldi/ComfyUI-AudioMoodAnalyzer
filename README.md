# ComfyUI Audio Mood Analyzer

A ComfyUI custom node that extracts sonic features from audio and uses a local Ollama LLM to generate painterly, emotionally-driven image-generation prompts.

Two nodes are available under **audio/analysis**:

- **Audio Mood Analyzer** — standard node with style presets
- **Audio Mood Analyzer (Advanced)** — adds optional full prompt template overrides

## Requirements

- [Ollama](https://ollama.com/) running locally with a model loaded (default: `qwen3:14b`)
- Python packages: `librosa`, `soundfile`, `numpy`, `requests`

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/andrea-spoldi/ComfyUI-AudioMoodAnalyzer.git
pip install -r ComfyUI-AudioMoodAnalyzer/requirements.txt
```

Restart ComfyUI. Both nodes appear under **audio/analysis**.

## How it works

The pipeline runs in two phases:

1. **Analysis** — extracts sonic features from the audio (tempo, energy, brightness, dynamics, etc.) and optionally analyzes lyrics/text. Both steps produce structured JSON used as context for the next phase.
2. **Generation** — uses the analysis JSON to generate up to three image-generation prompts: environment-only, subject-only, and a merged final prompt.

The two phases use separate temperature and context settings so that structured analysis stays consistent while creative generation stays expressive.

## Inputs

### Connection and model

| Name | Type | Description |
|------|------|-------------|
| `audio` | AUDIO | Audio input from any ComfyUI audio loader |
| `ollama_url` | STRING | Ollama API endpoint (default: `http://localhost:11434/api/generate`) |
| `model` | STRING | Ollama model name (default: `qwen3:14b`) |
| `analysis_temperature` | FLOAT | Temperature for structured JSON analysis calls — lower = more consistent (default: `0.4`) |
| `prompt_temperature` | FLOAT | Temperature for creative image-prompt generation — higher = more expressive (default: `0.8`) |

### Analysis context

These fields are injected into the **analysis phase only** and have no effect on the visual style of the output prompts.

| Name | Type | Description |
|------|------|-------------|
| `custom_context` | STRING | Analytical direction for the mood analysis (e.g. "focus on rhythm over atmosphere") |
| `lyrics_or_text` | STRING | Full lyrics or source text for subject analysis |
| `focus_fragment` | STRING | Key line or phrase used as the primary emotional/visual anchor |
| `song_title` | STRING | Song title used as thematic and symbolic context |
| `song_description` | STRING | General meaning, emotional arc, or artist intent |
| `song_genre` | STRING | Genre or style (e.g. "post-punk, shoegaze") |

Subject analysis only runs when at least one of `lyrics_or_text`, `focus_fragment`, `song_title`, `song_description`, or `song_genre` is provided.

### Style

These fields control the **aesthetic output** of the three image-generation prompts.

| Name | Type | Description |
|------|------|-------------|
| `style_preset` | COMBO | Visual aesthetic target: `painterly`, `cinematic`, `raw`, `abstract`, or `custom` (default: `painterly`) |
| `style_notes` | STRING | Optional free text appended to the preset, or used alone when preset is `custom` |

**Presets:**

| Preset | Target aesthetic |
|--------|-----------------|
| `painterly` | Oil painting, raw brushwork, emotionally loaded colour — Bacon, Schiele, Freud |
| `cinematic` | Wide cinematic frame, dramatic lighting, filmic grain — Tarkovsky, Wong Kar-wai, Villeneuve |
| `raw` | Visceral, lo-fi, grainy, desaturated — no production value |
| `abstract` | Non-representational, gestural, colour field — Rothko, Kiefer, Twombly |
| `custom` | Uses `style_notes` only |

### Output toggles

| Name | Type | Description |
|------|------|-------------|
| `generate_environment_prompt` | BOOLEAN | Generate an environment-only image prompt (default: `true`) |
| `generate_subject_prompt` | BOOLEAN | Generate a subject-only image prompt (default: `true`) |
| `generate_merge_prompt` | BOOLEAN | Generate a merged final image prompt (default: `true`) |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| `mood_json` | STRING | Full sonic mood analysis as JSON |
| `subject_json` | STRING | Subject analysis from lyrics/text as JSON |
| `environment_prompt` | STRING | Image prompt focused on environment/atmosphere |
| `subject_prompt` | STRING | Image prompt focused on the human subject |
| `merge_prompt` | STRING | Unified final image-generation prompt |
| `summary` | STRING | Short human-readable mood summary |

## Audio Mood Analyzer (Advanced)

The Advanced node exposes five optional **prompt template override** fields — one for each internal Ollama call. Leave a field empty to use the built-in template; provide a value to replace it entirely.

| Override field | Replaces | Available template variables |
|----------------|----------|------------------------------|
| `mood_prompt_override` | Audio mood analysis prompt | `{features}`, `{custom_context}`, `{style_block}` |
| `subject_analysis_prompt_override` | Subject analysis prompt | `{lyrics_or_text}`, `{focus_fragment}`, `{song_title}`, `{song_description}`, `{song_genre}`, `{custom_context}` |
| `environment_prompt_override` | Environment image-gen prompt | `{mood_json}`, `{subject_json}`, `{style_block}` |
| `subject_prompt_override` | Subject image-gen prompt | `{subject_json}`, `{style_block}` |
| `merge_prompt_override` | Merge/final image-gen prompt | `{mood_summary}`, `{environment_prompt}`, `{subject_prompt}`, `{style_block}` |

Use standard Python `{variable_name}` placeholders. If a variable name is not recognised, the node logs a warning and falls back to the built-in template for that call.

## Audio Mood Analyzer (Timeline)

Divides audio into N equal segments and runs the full analysis + generation pipeline on each. Designed for image sequence and video generation workflows.

### Additional input

| Name | Type | Description |
|------|------|-------------|
| `n_segments` | INT | Number of equal time segments to analyse (default: 8, range: 2–32) |

All other inputs are identical to the standard node.

### Outputs

| Name | Type | Description |
|------|------|-------------|
| `prompt_sequence_json` | STRING | JSON array — one object per segment containing `segment`, `start_s`, `end_s`, `mood_json`, `environment_prompt`, `subject_prompt`, `merge_prompt` |
| `merge_prompts` | STRING | Merge prompts only, newline-separated — one per segment |
| `environment_prompts` | STRING | Environment prompts only, newline-separated — one per segment |
| `subject_prompt` | STRING | Single shared subject prompt (computed once from lyrics, same across all segments) |

### Pipeline

Subject analysis runs **once** from lyrics/text. Mood analysis and prompt generation run **per segment**. At `n_segments=8`: up to 26 Ollama calls total.

`merge_prompts` is the most useful output for image batch nodes. `prompt_sequence_json` feeds the AnimateDiff formatter (see upcoming T-006 node).

### Sample workflow

`example_workflow/example_timeline.json` — shows the timeline node with all outputs displayed, and `merge_prompts` wired into a single-image sanity-check generation. Full per-frame image sequences require the AnimateDiff formatter node (T-006).

## AnimateDiff Schedule Formatter

Converts `AudioMoodAnalyzerTimeline`'s `prompt_sequence_json` output into an AnimateDiff Evolved (ADE) prompt travel schedule string. Each audio segment is proportionally mapped to a frame number within the AnimateDiff frame range.

### Inputs

| Name | Type | Description |
|------|------|-------------|
| `prompt_sequence_json` | STRING | JSON array from `Audio Mood Analyzer (Timeline)` |
| `total_frames` | INT | Must match the AnimateDiff frame count setting (default: 64, range: 8–256) |
| `prompt_type` | COMBO | Which prompt to use per segment: `merge_prompt` (default), `environment_prompt`, or `subject_prompt` |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| `schedule` | STRING | ADE prompt travel schedule — wire into an AnimateDiff Evolved prompt scheduling node |
| `first_frame_prompt` | STRING | Prompt for frame 0 — wire into a standard `CLIPTextEncode` as fallback positive conditioning |

### Output format

```
"0": "dark wasteland, crumbling concrete",
"8": "burning field, ash and smoke",
"16": "flooded ruin, grey water",
```

Frame numbers are derived proportionally: `frame = round(start_s / total_duration × total_frames)`. Empty prompts (if Ollama failed for a segment) are omitted. When two segments map to the same frame, the later segment's prompt wins.

### Sample workflow

`example_workflow/example_animatediff.json` — shows the full pipeline: `LoadAudio` → `AudioMoodAnalyzerTimeline` → `AnimateDiffScheduleFormatter` → schedule preview + single-image sanity check using `first_frame_prompt`.

## License

MIT — see [LICENSE](LICENSE).
