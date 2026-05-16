# Design: README Refinement (T-008)

**Date:** 2026-05-16
**Status:** approved
**Scope:** `README.md` only — no code changes

---

## Purpose

The README currently reads as feature documentation — a catalog of inputs,
outputs, and parameters. It does not communicate *why this project exists*,
*what problem it is trying to solve*, or *what kind of user it is for*.

T-008 rewrites the README to lead with philosophy and intent, frame the
project's experimental nature honestly, and only then descend into node
documentation. The goal: a reader who knows nothing about ComfyUI or audio
analysis should understand what this tool is *trying to do* and why that
matters before they encounter a single parameter table.

---

## Guiding principles for the new README

1. **Lead with the idea, not the features.** The first 200 words should
   communicate the project's artistic and philosophical ambition — translating
   emotional audio intelligence into visual form.

2. **Name the experiment.** This is not a polished product. The README must
   say so explicitly, in the opening section, not buried in a disclaimer at
   the bottom. Framing it as experimental is part of the brand.

3. **Explain the pipeline as a creative act.** Not as "it runs two phases"
   but as: audio has emotional content — we listen to it systematically, then
   ask a language model to imagine what that emotion looks like.

4. **Place CLAP in the bigger picture.** CLAP is not just a new node — it is
   a different way of listening (semantic rather than acoustic). The README
   should explain this distinction and why it matters alongside librosa.

5. **Keep reference tables.** The existing parameter tables are useful.
   Preserve them, but subordinate them to the narrative.

---

## Structure of the revised README

### Section 1: What is this?

Opening paragraph (4–6 sentences). Answers: what does this tool do, who made
it and why, what is the creative idea, what does it produce.

Key ideas to convey:
- Audio carries emotional intelligence that most tools ignore
- This project listens to that intelligence systematically
- It turns what it hears into language a diffusion model can act on
- It is experimental — results vary, surprises are expected

### Section 2: The idea behind it

Prose, not a table. 2–4 paragraphs. Covers:
- The pipeline concept: acoustic features → language model interpretation →
  image-generation prompts
- Why two phases (analysis vs generation) and why that matters
- The CLAP layer: semantic audio understanding as a complement to acoustic
  feature extraction — "this resembles nocturnal fear" vs "spectral centroid: 2400Hz"
- The philosophy of "semantic pressure": CLAP and librosa provide pressure on
  the LLM's interpretation, not instructions to the diffusion model

### Section 3: How it works (pipeline diagram)

Simplified ASCII diagram showing the flow:

```
audio
 ├─ librosa → acoustic features (tempo, energy, brightness…)
 └─ CLAP    → semantic anchors  (nocturnal fear, dark atmospheric tension…)
                     ↓
             Ollama LLM (Qwen / any model)
                     ↓
        mood_json + subject_json
                     ↓
  environment_prompt / subject_prompt / merge_prompt
```

### Section 4: Nodes

One sub-section per node. For each:
- One-sentence purpose
- Full input/output tables (existing content, cleaned up)
- Any node-specific notes

Nodes covered:
1. Audio Mood Analyzer (base)
2. Audio Mood Analyzer Advanced
3. Audio Mood Analyzer Timeline
4. AnimateDiff Schedule Formatter
5. CLAP Audio Analyzer (new — T-007)
6. Ollama Model Selector

### Section 5: Example workflows

Brief description of each example_workflow JSON file and what it demonstrates.
Currently: `example.json`, `example_timeline.json`, `example_animatediff.json`.
After T-007: add `example_clap.json`.

### Section 6: Requirements and installation

Same as now, updated to include `transformers>=4.35.0` (for CLAP node).

### Section 7: A note on results

A short honest section. Covers:
- Output quality depends heavily on the Ollama model used
- CLAP embeddings are powerful but not deterministic
- Prompt outputs are starting points, not finished images
- The project is intentionally permissive — results should surprise you

### Section 8: License

MIT, same as now.

---

## Tone guidelines

- First person plural is fine ("we try", "the idea is")
- Avoid marketing language ("powerful", "amazing", "state of the art")
- Favor honest uncertainty over false confidence
- Short paragraphs, plain sentences
- Tables for reference, prose for explanation

---

## Out of scope

- Any code changes
- Changelog or version history section
- Contributing guide
- CI badges or shields
