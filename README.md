# fear-of-the-art: Audio Analyzer

A ComfyUI custom node project that extracts sonic features from audio and uses a local Ollama LLM to generate painterly, emotionally-driven image-generation prompts. It is an experiment in taking audio seriously as a source of visual instruction — not just as a trigger, but as something that carries meaning worth listening to. Acoustic analysis via librosa describes what the audio does physically; optional CLAP embeddings describe what it feels like semantically; a local language model translates both into image-generation prose. The project is intentionally experimental: results vary, some outputs will surprise you, and that is part of the point.

---

## The idea behind it

Most audio-to-image tools treat audio as metadata — a filename, a BPM, a duration. This project treats audio as emotional content. The idea is that if you listen carefully enough to a piece of audio, you can describe what it *feels like*, and from that description, ask a diffusion model to make something that *looks* like it feels.

The pipeline works in two phases. First, acoustic features are extracted from the audio — tempo, spectral energy, brightness, dynamic range, textural complexity. These features are passed to a local LLM, which interprets them as mood data and produces structured JSON. Second, that JSON is used as context for a second LLM call that generates image-generation prompts in prose. The two phases use separate temperature settings: analysis calls use low temperature (0.4) for consistency, while prompt generation uses high temperature (0.8) to keep the visual output expressive and non-repetitive.

The CLAP node adds a second kind of listening. Where librosa measures *what* the audio does physically — "spectral centroid: 2400Hz", "onset rate: 3.2 per second" — CLAP measures what it *feels like* semantically. It compares the audio's embedding against a configurable set of text anchors ("nocturnal fear", "dark atmospheric tension", "explosive catharsis") and returns the ones that match most closely. The result is not an analysis of sonic properties but a vocabulary of affect.

CLAP and librosa are inputs to the LLM, not outputs of the pipeline. They apply pressure on the LLM's interpretation — they tell it what to pay attention to. The LLM decides what that means visually. This distinction matters: the system is not retrieving images that match an audio embedding; it is asking a language model to imagine a visual world from what the audio communicates.

---

## How it works

```
audio
 ├─ librosa → acoustic features  (tempo, energy, brightness, dynamics…)
 └─ CLAP    → semantic anchors   (nocturnal fear, dark atmospheric tension…)
                     ↓
             Ollama LLM (Qwen / any model)
                     ↓
        mood_json + subject_json
                     ↓
  environment_prompt / subject_prompt / merge_prompt
```

CLAP is optional — the pipeline runs without it. When present, its semantic anchors and the librosa features both reach the LLM in a single analysis call, which produces structured mood data used to drive up to three prompt-generation calls: environment, subject, and merged final.

---

## Nodes

### Audio Mood Analyzer

The base node. Extracts acoustic features from audio and uses a local Ollama LLM to generate up to three image-generation prompts: environment-only, subject-only, and a merged final prompt.

#### Connection and model

| Name | Type | Description |
|------|------|-------------|
| `audio` | AUDIO | Audio input from any ComfyUI audio loader |
| `ollama_url` | STRING | Ollama API endpoint (default: `http://localhost:11434/api/generate`) |
| `model` | STRING | Ollama model name (default: `qwen3:14b`) |
| `analysis_temperature` | FLOAT | Temperature for structured JSON analysis calls — lower = more consistent (default: `0.4`) |
| `prompt_temperature` | FLOAT | Temperature for creative image-prompt generation — higher = more expressive (default: `0.8`) |

#### Analysis context

These fields are injected into the analysis phase only and have no effect on the visual style of the output prompts.

| Name | Type | Description |
|------|------|-------------|
| `custom_context` | STRING | Analytical direction for the mood analysis (e.g. "focus on rhythm over atmosphere") |
| `lyrics_or_text` | STRING | Full lyrics or source text for subject analysis |
| `focus_fragment` | STRING | Key line or phrase used as the primary emotional/visual anchor |
| `song_title` | STRING | Song title used as thematic and symbolic context |
| `song_description` | STRING | General meaning, emotional arc, or artist intent |
| `song_genre` | STRING | Genre or style (e.g. "post-punk, shoegaze") |

Subject analysis only runs when at least one of `lyrics_or_text`, `focus_fragment`, `song_title`, `song_description`, or `song_genre` is provided.

#### Style

These fields control the aesthetic output of the three image-generation prompts.

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

#### Output toggles

| Name | Type | Description |
|------|------|-------------|
| `generate_environment_prompt` | BOOLEAN | Generate an environment-only image prompt (default: `true`) |
| `generate_subject_prompt` | BOOLEAN | Generate a subject-only image prompt (default: `true`) |
| `generate_merge_prompt` | BOOLEAN | Generate a merged final image prompt (default: `true`) |

#### Outputs

| Name | Type | Description |
|------|------|-------------|
| `mood_json` | STRING | Full sonic mood analysis as JSON |
| `subject_json` | STRING | Subject analysis from lyrics/text as JSON |
| `environment_prompt` | STRING | Image prompt focused on environment/atmosphere |
| `subject_prompt` | STRING | Image prompt focused on the human subject |
| `merge_prompt` | STRING | Unified final image-generation prompt |
| `summary` | STRING | Short human-readable mood summary |

---

### Audio Mood Analyzer (Advanced)

Identical to the base node (all inputs and outputs from the standard node apply), plus five optional prompt template override fields — one for each internal Ollama call. Leave a field empty to use the built-in template; provide a value to replace it entirely.

| Override field | Replaces | Available template variables |
|----------------|----------|------------------------------|
| `mood_prompt_override` | Audio mood analysis prompt | `{features}`, `{custom_context}`, `{style_block}` |
| `subject_analysis_prompt_override` | Subject analysis prompt | `{lyrics_or_text}`, `{focus_fragment}`, `{song_title}`, `{song_description}`, `{song_genre}`, `{custom_context}` |
| `environment_prompt_override` | Environment image-gen prompt | `{mood_json}`, `{subject_json}`, `{style_block}` |
| `subject_prompt_override` | Subject image-gen prompt | `{subject_json}`, `{style_block}` |
| `merge_prompt_override` | Merge/final image-gen prompt | `{mood_summary}`, `{environment_prompt}`, `{subject_prompt}`, `{style_block}` |

Use standard Python `{variable_name}` placeholders. If a variable name is not recognised, the node logs a warning and falls back to the built-in template for that call.

---

### Audio Mood Analyzer (Timeline)

Divides audio into N equal segments and runs the full analysis and generation pipeline on each. Subject analysis runs once from lyrics/text; mood analysis and prompt generation run per segment. Designed for image sequence and video generation workflows.

#### Additional input

| Name | Type | Description |
|------|------|-------------|
| `n_segments` | INT | Number of equal time segments to analyse (default: 8, range: 2–32) |

All other inputs are identical to the standard node.

#### Outputs

| Name | Type | Description |
|------|------|-------------|
| `prompt_sequence_json` | STRING | JSON array — one object per segment containing `segment`, `start_s`, `end_s`, `mood_json`, `environment_prompt`, `subject_prompt`, `merge_prompt` |
| `merge_prompts` | STRING | Merge prompts only, newline-separated — one per segment |
| `environment_prompts` | STRING | Environment prompts only, newline-separated — one per segment |
| `subject_prompt` | STRING | Single shared subject prompt (computed once from lyrics, same across all segments) |

At `n_segments=8` with all toggles on: up to 26 Ollama calls total (2 shared subject calls + 3 per-segment calls × 8 segments). `merge_prompts` is the most useful output for image batch nodes. `prompt_sequence_json` feeds the AnimateDiff Schedule Formatter.

---

### AnimateDiff Schedule Formatter

Converts `AudioMoodAnalyzerTimeline`'s `prompt_sequence_json` output into an AnimateDiff Evolved (ADE) prompt travel schedule string. Each audio segment is proportionally mapped to a frame number within the AnimateDiff frame range.

#### Inputs

| Name | Type | Description |
|------|------|-------------|
| `prompt_sequence_json` | STRING | JSON array from `Audio Mood Analyzer (Timeline)` |
| `total_frames` | INT | Must match the AnimateDiff frame count setting (default: 64, range: 8–256) |
| `prompt_type` | COMBO | Which prompt to use per segment: `merge_prompt` (default), `environment_prompt`, or `subject_prompt` |

#### Outputs

| Name | Type | Description |
|------|------|-------------|
| `schedule` | STRING | ADE prompt travel schedule — wire into an AnimateDiff Evolved prompt scheduling node |
| `first_frame_prompt` | STRING | Prompt for frame 0 — wire into a standard `CLIPTextEncode` as fallback positive conditioning |

#### Output format

```
"0": "dark wasteland, crumbling concrete",
"8": "burning field, ash and smoke",
"16": "flooded ruin, grey water",
```

Frame numbers are derived proportionally: `frame = round(start_s / total_duration × total_frames)`. Empty prompts (if Ollama failed for a segment) are omitted. When two segments map to the same frame, the later segment's prompt wins.

---

### CLAP Audio Analyzer

Extracts a semantic audio embedding using CLAP and ranks a configurable set of text anchors by cosine similarity to the audio. Designed to feed its `semantic_summary` output into `AudioMoodAnalyzer.custom_context`, adding semantic pressure to the LLM's interpretation without overriding the acoustic analysis.

#### Inputs

| Name | Type | Description |
|------|------|-------------|
| `audio` | AUDIO | Audio from any ComfyUI audio loader |
| `clap_model` | STRING | HuggingFace model ID (default: `laion/clap-htsat-unfused`) |
| `clap_device` | COMBO | `auto`, `cpu`, `cuda`, or `mps` (default: `auto`) |
| `clap_text_anchors` | STRING (multiline) | One anchor phrase per line — ranked against the audio |

Default anchors (15 phrases): dark atmospheric tension, melancholic isolation, aggressive emotional pressure, fragile human vulnerability, nocturnal fear, ritualistic heaviness, dreamlike surreal space, claustrophobic anxiety, slow emotional collapse, explosive catharsis, cold empty space, distorted memory, spiritual dread, submerged sadness, violent inner pressure

#### Outputs

| Name | Type | Description |
|------|------|-------------|
| `clap_json` | STRING | Full JSON — model name, embedding norm, ranked matches, top-3 inference |
| `semantic_summary` | STRING | `"CLAP: anchor1, anchor2, anchor3"` — wire into `AudioMoodAnalyzer.custom_context` |

Wiring `semantic_summary` into `AudioMoodAnalyzer.custom_context` injects the top-3 anchor phrases into the LLM's mood analysis prompt as named emotional vocabulary — the same "semantic pressure" mechanism described above, but sourced from the audio embedding rather than typed by hand.

The model is loaded once per ComfyUI session (the Python process lifetime, not per workflow run) and cached by (model_name, device) — changing the device mid-session has no effect until ComfyUI restarts. On error, `semantic_summary` returns `""` and the workflow continues.

---

### Ollama Model Selector

Queries a local Ollama server and returns the list of installed model names. Useful for wiring the correct model name into analysis nodes without hardcoding it.

#### Inputs

| Name | Type | Description |
|------|------|-------------|
| `ollama_url` | STRING | Ollama base URL (default: `http://localhost:11434`) |

#### Outputs

| Name | Type | Description |
|------|------|-------------|
| `models_list` | STRING | Newline-separated list of installed model names |
| `first_model` | STRING | First model name — wire directly into `AudioMoodAnalyzer.model` |

---

## Example workflows

| File | Demonstrates |
|------|-------------|
| `example_workflow/example.json` | Standard dual conditioning — environment + subject as separate CLIPTextEncode inputs, averaged via ConditioningAverage |
| `example_workflow/example_timeline.json` | Full-song timeline analysis, n_segments=8, merge_prompts wired to a single-image sanity check |
| `example_workflow/example_animatediff.json` | Timeline → AnimateDiff formatter → ADE schedule string preview + first_frame_prompt as positive conditioning |
| `example_workflow/example_clap.json` | CLAP semantic embedding — semantic_summary output shown via PreviewAny, ready to wire into AudioMoodAnalyzer.custom_context |

---

## Requirements and installation

**Requirements:**

- [Ollama](https://ollama.com/) running locally with a model loaded (default: `qwen3:14b`)
- Python packages: `librosa`, `soundfile`, `numpy`, `requests`, `transformers>=4.35.0`

**Installation:**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/andrea-spoldi/ComfyUI-AudioMoodAnalyzer.git
pip install -r ComfyUI-AudioMoodAnalyzer/requirements.txt
```

Restart ComfyUI. All nodes appear under **audio/analysis**.

---

## A note on results

Output quality depends heavily on the Ollama model — larger, instruction-tuned models produce more coherent and visually specific prompts, while smaller models tend toward generic language. CLAP anchors apply semantic pressure on the LLM's interpretation, but they are not guarantees: the model may weight them lightly or interpret them in unexpected directions. The prompts this pipeline produces are starting points, not finished images — they will need refinement for production use. Surprises are expected and are often more interesting than what a more deterministic system would produce.

---

## License

MIT — see [LICENSE](LICENSE).
