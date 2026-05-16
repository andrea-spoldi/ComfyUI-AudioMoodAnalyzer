# Design: ClapAudioAnalyzer — Standalone CLAP Integration (T-007)

**Date:** 2026-05-16
**Status:** approved
**Node:** `ClapAudioAnalyzer` (new standalone node, same file/project)
**Integration:** Option A — zero changes to existing nodes. Output wired via `custom_context`.

---

## Purpose

Add semantic audio understanding to the pipeline using CLAP (Contrastive
Language-Audio Pretraining). CLAP operates at a higher semantic level than
librosa — it can say "this audio resembles nocturnal fear" rather than
"spectral centroid: 2400Hz". The two signals are complementary: librosa
captures acoustic structure, CLAP captures emotional semantics.

The node is standalone and optional. It produces a `semantic_summary` string
designed to be wired into `AudioMoodAnalyzer`'s `custom_context` input,
giving Qwen semantic pressure alongside the raw acoustic features — without
any modifications to existing nodes or workflows.

---

## Architecture

Completely standalone class — no inheritance, no Ollama calls, no audio
extraction shared with other nodes. Self-contained.

Two module-level helpers extracted for testability:
- `_resolve_clap_device(device_str) -> str`
- `_get_clap_model(model_name, device_str) -> (model, processor)` — uses global cache

Global model cache:
```python
_CLAP_MODEL_CACHE: dict[tuple, tuple] = {}
```
Key: `(model_name, resolved_device_str)`. Survives across workflow executions
within the same ComfyUI session. Models are loaded once and reused.

---

## Dependency

Uses HuggingFace `transformers` (`ClapModel` + `ClapProcessor`). NOT the
`laion-clap` package. `transformers` is already a standard dependency in
ComfyUI environments; `ClapModel` is available since transformers ≥ 4.35.

`requirements.txt` addition: `transformers>=4.35.0`

`torch` is not added — it is already present in any ComfyUI installation.

---

## Inputs

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `audio` | AUDIO | — | Audio input from any ComfyUI audio loader |
| `clap_model` | STRING | `"laion/clap-htsat-unfused"` | HuggingFace model ID |
| `clap_device` | COMBO | `"auto"` | `["auto", "cpu", "cuda", "mps"]` |
| `clap_text_anchors` | STRING (multiline) | *(see below)* | One anchor phrase per line |

**Default `clap_text_anchors`:**
```
dark atmospheric tension
melancholic isolation
aggressive emotional pressure
fragile human vulnerability
nocturnal fear
ritualistic heaviness
dreamlike surreal space
claustrophobic anxiety
slow emotional collapse
explosive catharsis
cold empty space
distorted memory
spiritual dread
submerged sadness
violent inner pressure
```

---

## Outputs

| Name | Type | Description |
|------|------|-------------|
| `clap_json` | STRING | Full JSON — embedding norm, ranked matches, semantic_inference |
| `semantic_summary` | STRING | Formatted string for wiring into `AudioMoodAnalyzer.custom_context` |

### `clap_json` schema — success

```json
{
  "enabled": true,
  "model": "laion/clap-htsat-unfused",
  "embedding_dim": 512,
  "audio_embedding_norm": 0.9997,
  "top_text_matches": [
    {"text": "dark atmospheric tension", "score": 0.34},
    {"text": "nocturnal fear", "score": 0.29},
    {"text": "fragile human vulnerability", "score": 0.21}
  ],
  "semantic_inference": [
    "dark atmospheric tension",
    "nocturnal fear",
    "fragile human vulnerability"
  ]
}
```

`semantic_inference` = top 3 anchors by cosine similarity score. Always
exactly 3 entries unless fewer anchors are provided.

### `clap_json` schema — error

```json
{
  "enabled": true,
  "error": "CLAP model failed to load: ...",
  "fallback": "librosa_only"
}
```

### `semantic_summary` format

```
CLAP: dark atmospheric tension, nocturnal fear, fragile human vulnerability
```

Prefixed with `"CLAP: "` so it remains identifiable when concatenated
with the user's existing `custom_context` via a Text Concatenate node.

On error: `semantic_summary` returns `""` (empty string).

---

## Device resolution

`"auto"` resolves at runtime:
1. `torch.cuda.is_available()` → `"cuda"`
2. `torch.backends.mps.is_available()` → `"mps"`
3. fallback → `"cpu"`

Cache key uses the resolved device string, not `"auto"`, so a
second call with `"auto"` that resolves to `"cuda"` reuses an existing
`"cuda"`-keyed cache entry.

---

## Implementation sketch

```python
# Audio extraction (inline — no shared helper needed)
waveform = audio["waveform"]
sr = int(audio["sample_rate"])
if hasattr(waveform, "detach"):
    waveform = waveform.detach().cpu().numpy()
y = np.asarray(waveform)
if y.ndim == 3: y = y[0]
if y.ndim == 2: y = np.mean(y, axis=0)
y = y.astype(np.float32)

# Model load (with progress log)
device = _resolve_clap_device(clap_device)
model, processor = _get_clap_model(clap_model, device)

# Audio embedding
audio_inputs = processor(audios=[y], sampling_rate=sr, return_tensors="pt").to(device)
with torch.no_grad():
    audio_emb = model.get_audio_features(**audio_inputs)
audio_emb = audio_emb / audio_emb.norm(dim=-1, keepdim=True)

# Text embeddings
anchors = [a.strip() for a in clap_text_anchors.strip().splitlines() if a.strip()]
text_inputs = processor(text=anchors, return_tensors="pt", padding=True).to(device)
with torch.no_grad():
    text_emb = model.get_text_features(**text_inputs)
text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)

# Similarity
scores = (audio_emb @ text_emb.T).squeeze(0).cpu().numpy()
ranked = sorted(zip(anchors, scores.tolist()), key=lambda x: -x[1])
top3 = ranked[:3]
```

---

## Error handling

All CLAP work is wrapped in a single `try/except Exception`. On failure:
- `clap_json` = `{"enabled": true, "error": "...", "fallback": "librosa_only"}`
- `semantic_summary` = `""`
- Log warning with `_LOG` prefix
- Node returns normally — does NOT raise

---

## Sample workflow: `example_workflow/example_clap.json`

Shows the integration pattern:

```
LoadAudio → ClapAudioAnalyzer
    ├─ clap_json         → PreviewAny (inspect full JSON)
    └─ semantic_summary  → Text Concatenate
                              ↑ (also receives user's custom_context text)
                              ↓
                         AudioMoodAnalyzer.custom_context
```

Model stack: same as other example workflows (zImageTurbo, qwen_3_4b,
ae.safetensors, fear_of_the_art LoRA disabled). `OllamaModelSelector`
included for model discovery.

---

## Registration

```python
NODE_CLASS_MAPPINGS["ClapAudioAnalyzer"] = ClapAudioAnalyzer
NODE_DISPLAY_NAME_MAPPINGS["ClapAudioAnalyzer"] = "CLAP Audio Analyzer"
```

Category: `audio/analysis`

---

## Out of scope

- Exposing the raw embedding tensor as a ComfyUI type (`CLAP_EMBEDDING`)
- Timestamp-aware / per-segment CLAP (future: integrates with Timeline node)
- Auto fragment selection
- Multi-model voting
- Any changes to `AudioMoodAnalyzer`, `AudioMoodAnalyzerAdvanced`, or `AudioMoodAnalyzerTimeline`
