# README Refinement Implementation Plan (T-008)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `README.md` to lead with philosophy and intent — what this tool is trying to do and why — before descending into node documentation. Add CLAP Audio Analyzer docs. Preserve all existing reference tables.

**Architecture:** Pure documentation rewrite. No code changes. Single file: `README.md`.

**Tech Stack:** Markdown only.

---

## File map

- **Rewrite:** `README.md` — complete restructure as defined in the spec

---

### Task 1: Write the new README

**Files:**
- Rewrite: `README.md`

This is a single-task plan. The README is rewritten top-to-bottom following the spec structure.

- [ ] **Step 1: Read the current README and the spec**

Read:
- `/Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer/README.md`
- `/Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer/docs/superpowers/specs/2026-05-16-readme-refinement-design.md`

Do not start writing until both are read.

- [ ] **Step 2: Write the new README**

Write the complete new README to `README.md`. Follow this structure exactly:

**Section 1: What is this?** (4–6 sentence opening paragraph)

Key ideas:
- Audio carries emotional intelligence that most tools ignore
- This project listens systematically using librosa (acoustic features) + CLAP (semantic anchors) + a local LLM
- It turns what it hears into language a diffusion model can act on
- It is intentionally experimental — results vary, surprises are expected and welcome

Opening must name this is a ComfyUI custom node project.

**Section 2: The idea behind it** (prose, 2–4 paragraphs)

Cover in order:
1. The pipeline concept: acoustic features → LLM interpretation → image prompts. The LLM is not given a waveform — it is given a description of what the audio *does*: tempo, energy, brightness, dynamic range, spectral texture. From that, it imagines what the audio *looks like*.
2. Why two phases: analysis (low temperature, structured JSON) vs generation (high temperature, creative prose). The split keeps structured analysis consistent while letting visual generation stay expressive.
3. The CLAP layer: "where librosa measures *what* the audio does physically, CLAP measures what it *feels like* semantically. Feeding both into the LLM gives it richer pressure." Contrast example: "spectral centroid: 2400Hz" vs "nocturnal fear".
4. The philosophy of semantic pressure: CLAP and librosa are inputs, not outputs. They tell the LLM what to consider. The LLM decides what that means visually.

**Section 3: How it works** (ASCII pipeline diagram)

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

Add 1-2 sentences after the diagram explaining what feeds into what.

**Section 4: Nodes** (one sub-section per node, in this order)

For each node: one-sentence purpose, then full input/output tables. Preserve all existing table content. Update for CLAP Audio Analyzer (new node).

Node order:
1. Audio Mood Analyzer (base)
2. Audio Mood Analyzer (Advanced)
3. Audio Mood Analyzer (Timeline)
4. AnimateDiff Schedule Formatter
5. CLAP Audio Analyzer

**CLAP Audio Analyzer section** — new content:

Purpose: Extracts a semantic audio embedding using CLAP (Contrastive Language-Audio Pretraining) and ranks a configurable set of text anchors by similarity to the audio. Designed to wire its `semantic_summary` output into `AudioMoodAnalyzer.custom_context` via a Text Concatenate node.

Inputs:

| Name | Type | Description |
|------|------|-------------|
| `audio` | AUDIO | Audio input from any ComfyUI audio loader |
| `clap_model` | STRING | HuggingFace model ID (default: `laion/clap-htsat-unfused`) |
| `clap_device` | COMBO | `auto`, `cpu`, `cuda`, or `mps` (default: `auto`) |
| `clap_text_anchors` | STRING (multiline) | One anchor phrase per line — ranked against the audio embedding |

Default anchors (15 phrases covering a broad emotional-sonic range):
```
dark atmospheric tension, melancholic isolation, aggressive emotional pressure,
fragile human vulnerability, nocturnal fear, ritualistic heaviness,
dreamlike surreal space, claustrophobic anxiety, slow emotional collapse,
explosive catharsis, cold empty space, distorted memory,
spiritual dread, submerged sadness, violent inner pressure
```

Outputs:

| Name | Type | Description |
|------|------|-------------|
| `clap_json` | STRING | Full JSON — model name, embedding norm, ranked matches, top-3 semantic inference |
| `semantic_summary` | STRING | `"CLAP: anchor1, anchor2, anchor3"` — wire into `AudioMoodAnalyzer.custom_context` |

The model is loaded once per session and cached. On error, `semantic_summary` returns `""` and the workflow continues uninterrupted.

6. Ollama Model Selector — add this section (currently missing from README)

Purpose: Queries a local Ollama server and returns a list of installed model names. Useful for wiring the correct model name into other nodes without hardcoding it.

Inputs:

| Name | Type | Description |
|------|------|-------------|
| `ollama_url` | STRING | Ollama API endpoint (default: `http://localhost:11434`) |

Outputs:

| Name | Type | Description |
|------|------|-------------|
| `models_list` | STRING | Newline-separated list of installed model names |
| `first_model` | STRING | Name of the first model — wire directly into `AudioMoodAnalyzer.model` |

**Section 5: Example workflows**

| File | Demonstrates |
|------|-------------|
| `example_workflow/example.json` | Standard dual conditioning — environment + subject as separate CLIPTextEncode inputs, averaged via ConditioningAverage |
| `example_workflow/example_timeline.json` | Full-song timeline analysis, `n_segments=8`, `merge_prompts` wired to a single-image sanity check |
| `example_workflow/example_animatediff.json` | Timeline → AnimateDiff formatter → ADE schedule string preview + `first_frame_prompt` as positive conditioning |
| `example_workflow/example_clap.json` | CLAP semantic embedding → `semantic_summary` wired into `custom_context` alongside user text |

**Section 6: Requirements and installation**

Same as current. Update requirements to include `transformers>=4.35.0`.

**Section 7: A note on results**

Short honest section (3–5 sentences). Cover:
- Output quality depends heavily on the Ollama model — larger, instruction-tuned models produce better prompts
- CLAP anchors provide semantic *pressure*, not guarantees — the same audio can produce different top matches with different anchor sets
- Prompt outputs are starting points, not finished images; expect iteration
- The project is intentionally permissive — results that surprise you are often more interesting than results that don't

**Section 8: License**

MIT — see LICENSE.

- [ ] **Step 3: Review the written README**

After writing, read it back and verify:
- Opens with philosophy and intent (not feature list)
- Names the experimental nature in the first section
- CLAP node is documented
- OllamaModelSelector is documented
- All existing parameter tables are present and accurate
- `transformers>=4.35.0` appears in requirements

Fix any gaps in place.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README to lead with philosophy and intent; add CLAP and OllamaModelSelector docs"
```

---

## Self-review checklist (spec coverage)

- [x] Section 1: philosophy opening — Task 1 step 2 ✓
- [x] Experimental framing in opening — Task 1 step 2 ✓
- [x] Pipeline explanation as creative act — Task 1 step 2 ✓
- [x] CLAP vs librosa distinction explained — Task 1 step 2 ✓
- [x] Semantic pressure philosophy — Task 1 step 2 ✓
- [x] ASCII pipeline diagram — Task 1 step 2 ✓
- [x] All 6 nodes documented — Task 1 step 2 ✓
- [x] CLAP Audio Analyzer inputs/outputs — Task 1 step 2 ✓
- [x] OllamaModelSelector documented (was missing) — Task 1 step 2 ✓
- [x] Example workflows table with all 4 files — Task 1 step 2 ✓
- [x] transformers>=4.35.0 in requirements — Task 1 step 2 ✓
- [x] "Note on results" honest section — Task 1 step 2 ✓
- [x] Tone: no marketing language — Task 1 step 2 ✓
