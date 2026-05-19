# Composition Inference Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `CompositionInferenceNode` to `audio_mood_analyzer.py` — a standalone node that takes `mood_json` + `subject_json`, runs two Ollama calls to infer visual composition, and outputs `composition_json`, `composition_prompt`, `width` (INT), and `height` (INT).

**Architecture:** Two-call pipeline — Call 1 at `analysis_temperature` produces structured `composition_json`; Call 2 at `prompt_temperature` produces prose `composition_prompt`. `width`/`height` are parsed directly from `recommended_resolution` in the JSON. `CompositionInferenceNode` is a standalone class (no inheritance) that duplicates the three Ollama/JSON helpers from `AudioMoodAnalyzer` to avoid refactoring shared infrastructure.

**Tech Stack:** Python 3.x, requests, json — same stack as existing nodes. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-19-composition-inference-design.md`
**Tests:** Deferred to backlog task T-009.

---

### Task 1: Add `_parse_resolution` helper and `_COMPOSITION_FALLBACK` constant

**Files:**
- Modify: `audio_mood_analyzer.py` — insert after line 67 (after `_fmt_json`)

- [ ] **Step 1: Insert `_parse_resolution` and `_COMPOSITION_FALLBACK` after `_fmt_json`**

Open `audio_mood_analyzer.py`. After the `_fmt_json` function (line 67), insert:

```python
def _parse_resolution(resolution_str: str) -> tuple:
    try:
        for sep in ("×", "x"):
            if sep in resolution_str:
                w, h = resolution_str.split(sep, 1)
                return int(w.strip()), int(h.strip())
    except (ValueError, AttributeError):
        pass
    print(f"{_LOG} ⚠ could not parse resolution '{resolution_str}' — defaulting to 1024×1024")
    return 1024, 1024


_COMPOSITION_FALLBACK = {
    "aspect_ratio": {
        "orientation": "square",
        "ratio": "1:1",
        "recommended_resolution": "1024x1024",
    },
    "subject_placement": {"position": "center", "size_weight": 0.5},
    "environment": {"weight": 0.5, "negative_space": "medium"},
    "camera": {"distance": "medium", "framing_style": "balanced", "crop": "none"},
}
```

- [ ] **Step 2: Verify the file loads without errors**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer
python -c "import audio_mood_analyzer; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat(composition): add _parse_resolution helper and _COMPOSITION_FALLBACK"
```

---

### Task 2: Add `CompositionInferenceNode` class skeleton

**Files:**
- Modify: `audio_mood_analyzer.py` — insert new class before `NODE_CLASS_MAPPINGS` (currently line 1169, shifts as earlier tasks add lines)

- [ ] **Step 1: Insert the class skeleton before `NODE_CLASS_MAPPINGS`**

Find `NODE_CLASS_MAPPINGS = {` near the end of the file. Insert the following block immediately before it:

```python
class CompositionInferenceNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mood_json": ("STRING", {"multiline": True}),
                "subject_json": ("STRING", {"multiline": True}),
                "ollama_url": ("STRING", {
                    "default": "http://localhost:11434/api/generate"
                }),
                "model": ("STRING", {"default": "qwen3:14b"}),
                "analysis_temperature": ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.5, "step": 0.1
                }),
                "prompt_temperature": ("FLOAT", {
                    "default": 0.8, "min": 0.0, "max": 1.5, "step": 0.1
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("composition_json", "composition_prompt", "width", "height")
    FUNCTION = "infer"
    CATEGORY = "audio/analysis"
```

- [ ] **Step 2: Verify the file loads without errors**

```bash
python -c "import audio_mood_analyzer; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat(composition): add CompositionInferenceNode class skeleton"
```

---

### Task 3: Add Ollama/JSON helper methods to `CompositionInferenceNode`

**Files:**
- Modify: `audio_mood_analyzer.py` — add three instance methods inside `CompositionInferenceNode`

These methods are duplicated from `AudioMoodAnalyzer` because `CompositionInferenceNode` is standalone (no inheritance). They are small and self-contained.

- [ ] **Step 1: Add `_ollama_generate`, `_timed_generate`, `_extract_json` inside `CompositionInferenceNode`**

Inside the `CompositionInferenceNode` class (after the class-level attributes), add:

```python
    def _ollama_generate(self, ollama_url, model, prompt, temperature, num_predict=-1):
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": num_predict},
            },
            timeout=600,
        )
        response.raise_for_status()
        data = response.json()
        thinking = data.get("thinking", "")
        if thinking:
            print(f"{_LOG} [Composition]   thinking: {len(thinking)} chars")
        result = data.get("response", "").strip()
        if not result:
            print(f"{_LOG} [Composition] ⚠ empty response from Ollama")
        return result

    def _timed_generate(self, label, ollama_url, model, prompt, temperature):
        print(f"{_LOG} [Composition] ▶ {label}")
        t = time.time()
        result = self._ollama_generate(ollama_url, model, prompt, temperature)
        print(f"{_LOG} [Composition] ✓ {label}  ({time.time()-t:.1f}s, {len(result)} chars)")
        return result

    def _extract_json(self, text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        print(f"{_LOG} [Composition] ⚠ JSON parse failed ({len(text)} chars)")
        return {"error": "Could not parse model output as JSON", "raw_output": text}
```

- [ ] **Step 2: Verify the file loads without errors**

```bash
python -c "import audio_mood_analyzer; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat(composition): add Ollama/JSON helper methods to CompositionInferenceNode"
```

---

### Task 4: Add LLM prompt builder methods to `CompositionInferenceNode`

**Files:**
- Modify: `audio_mood_analyzer.py` — add two prompt builder methods inside `CompositionInferenceNode`

- [ ] **Step 1: Add `_build_composition_json_prompt` inside `CompositionInferenceNode`**

```python
    def _build_composition_json_prompt(self, mood_json, subject_json):
        subject_section = (
            f"Subject analysis (primary signal — inferred from lyrics, focus fragments, or song description):\n{_fmt_json(subject_json)}"
            if subject_json
            else "Subject analysis: not available — infer from mood alone, default to environment_dominant framing."
        )
        return f"""
You are an art director inferring visual composition from music analysis and lyrical subject material.

{subject_section}

Sonic mood analysis (supporting atmospheric context):
{_fmt_json(mood_json)}

Infer the optimal visual composition for an image that expresses this music.

Consider:
- Does the subject dominate, or does the environment carry the weight?
- What orientation and ratio best serves the emotional content?
- Where does the subject sit within the frame?
- How much negative space reinforces the mood?
- What camera distance and crop serve the subject?

Return only valid JSON with this exact structure:
{{
  "aspect_ratio": {{
    "orientation": "portrait",
    "ratio": "4:5",
    "recommended_resolution": "1024x1280"
  }},
  "subject_placement": {{
    "position": "lower_right",
    "size_weight": 0.35
  }},
  "environment": {{
    "weight": 0.65,
    "negative_space": "high"
  }},
  "camera": {{
    "distance": "medium",
    "framing_style": "environment_dominant",
    "crop": "waist_up"
  }}
}}

Constraints:
- orientation must be one of: portrait, landscape, square
- ratio must be one of: 4:5, 16:9, 9:16, 1:1, 3:2, 2:3
- recommended_resolution must be one of: 1024x1280, 1280x1024, 768x1344, 1344x768, 896x1152, 1152x896, 1024x1024, 832x1216, 1216x832
- position must be one of: center, lower_left, lower_right, upper_left, upper_right, off_frame
- negative_space must be one of: low, medium, high
- distance must be one of: close, medium, wide
- framing_style must be one of: subject_dominant, environment_dominant, balanced
- crop must be one of: full_body, waist_up, bust, face_only, none

If subject analysis is unavailable, set framing_style to environment_dominant and crop to none.

Do not include any text before or after the JSON.
"""
```

- [ ] **Step 2: Add `_build_composition_prose_request` inside `CompositionInferenceNode`**

```python
    def _build_composition_prose_request(self, composition_json):
        return f"""
You are an art director translating a composition analysis into image-generation prompt language.

Composition analysis:
{_fmt_json(composition_json)}

Write a short, precise image-generation prompt that describes:
- the framing and orientation
- where the subject sits in the frame (if present)
- the relationship between subject and environment
- camera distance and crop
- negative space quality

Keep it:
- concise (one to two sentences)
- visual and specific
- in image-generation prompt style (no explanation, no metadata)

Output only the final composition prompt.
"""
```

- [ ] **Step 3: Verify the file loads without errors**

```bash
python -c "import audio_mood_analyzer; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat(composition): add LLM prompt builder methods to CompositionInferenceNode"
```

---

### Task 5: Implement `infer` method on `CompositionInferenceNode`

**Files:**
- Modify: `audio_mood_analyzer.py` — add `infer` method inside `CompositionInferenceNode`

- [ ] **Step 1: Add `infer` method inside `CompositionInferenceNode`**

```python
    def infer(
        self,
        mood_json,
        subject_json,
        ollama_url,
        model,
        analysis_temperature,
        prompt_temperature,
    ):
        t0 = time.time()
        print(f"{_LOG} [Composition] model: {model}")

        try:
            mood = json.loads(mood_json) if isinstance(mood_json, str) else mood_json
        except (json.JSONDecodeError, TypeError):
            mood = {}

        try:
            subject = json.loads(subject_json) if isinstance(subject_json, str) else subject_json
        except (json.JSONDecodeError, TypeError):
            subject = {}

        if not subject:
            print(f"{_LOG} [Composition] ⚠ subject_json empty — inferring from mood only")

        raw_composition = self._timed_generate(
            "composition inference", ollama_url, model,
            self._build_composition_json_prompt(mood, subject),
            analysis_temperature,
        )
        composition = self._extract_json(raw_composition)

        if "error" in composition:
            print(f"{_LOG} [Composition] ⚠ falling back to safe composition defaults")
            composition = _COMPOSITION_FALLBACK

        width, height = _parse_resolution(
            composition.get("aspect_ratio", {}).get("recommended_resolution", "1024x1024")
        )

        composition_prompt = self._timed_generate(
            "composition prompt", ollama_url, model,
            self._build_composition_prose_request(composition),
            prompt_temperature,
        )

        if not composition_prompt.strip():
            print(f"{_LOG} [Composition] ⚠ empty composition prompt returned")

        print(f"{_LOG} [Composition] done  total: {time.time()-t0:.1f}s")

        return (
            _fmt_json(composition),
            composition_prompt,
            width,
            height,
        )
```

- [ ] **Step 2: Verify the file loads without errors**

```bash
python -c "import audio_mood_analyzer; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat(composition): implement infer method on CompositionInferenceNode"
```

---

### Task 6: Register `CompositionInferenceNode` in node mappings

**Files:**
- Modify: `audio_mood_analyzer.py` — update `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`

- [ ] **Step 1: Add `CompositionInferenceNode` to both mappings**

Find `NODE_CLASS_MAPPINGS` near the end of the file. Add the new entry:

```python
NODE_CLASS_MAPPINGS = {
    "AudioMoodAnalyzer": AudioMoodAnalyzer,
    "AudioMoodAnalyzerAdvanced": AudioMoodAnalyzerAdvanced,
    "AudioMoodAnalyzerTimeline": AudioMoodAnalyzerTimeline,
    "AnimateDiffScheduleFormatter": AnimateDiffScheduleFormatter,
    "OllamaModelSelector": OllamaModelSelector,
    "ClapAudioAnalyzer": ClapAudioAnalyzer,
    "CompositionInferenceNode": CompositionInferenceNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioMoodAnalyzer": "Audio Mood Analyzer",
    "AudioMoodAnalyzerAdvanced": "Audio Mood Analyzer (Advanced)",
    "AudioMoodAnalyzerTimeline": "Audio Mood Analyzer (Timeline)",
    "AnimateDiffScheduleFormatter": "AnimateDiff Schedule Formatter",
    "OllamaModelSelector": "Ollama Model Selector",
    "ClapAudioAnalyzer": "CLAP Audio Analyzer",
    "CompositionInferenceNode": "Composition Inference",
}
```

- [ ] **Step 2: Verify the node is exported correctly**

```bash
python -c "
from audio_mood_analyzer import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
assert 'CompositionInferenceNode' in NODE_CLASS_MAPPINGS
assert NODE_DISPLAY_NAME_MAPPINGS['CompositionInferenceNode'] == 'Composition Inference'
print('OK')
"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat(composition): register CompositionInferenceNode in node mappings"
```

---

### Task 7: Update TASKS.md backlog

**Files:**
- Modify: `TASKS.md` — add T-009 (tests) and record S-007 as the current session

- [ ] **Step 1: Add T-009 to the backlog and update `current_session`**

In `TASKS.md`, update the JSON block:
- Set `current_session` to `S-007`, goal `"Add CompositionInferenceNode"`, status `"done"`
- Add to `backlog`:

```json
{
  "id": "T-009",
  "title": "Tests for CompositionInferenceNode",
  "size": "S",
  "status": "pending",
  "notes": "See testing section in 2026-05-19-composition-inference-design.md. Mock _ollama_generate. Cover: all required JSON keys, orientation constraint, width/height match recommended_resolution, composition_prompt non-empty, fallback to 1024x1024 on malformed JSON, empty subject_json does not raise."
}
```

Also add to `completed[]`:

```json
{
  "id": "T-010",
  "title": "CompositionInferenceNode — core implementation",
  "completed_date": "2026-05-19",
  "session_ref": "S-007",
  "notes": "_parse_resolution, _COMPOSITION_FALLBACK, two-call pipeline, width/height INT outputs, composition_prompt STRING output."
}
```

- [ ] **Step 2: Commit**

```bash
git add TASKS.md
git commit -m "chore: update TASKS.md — T-009 (tests) in backlog, T-010 complete"
```
