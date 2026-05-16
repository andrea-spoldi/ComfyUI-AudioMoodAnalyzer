# Style Presets + Prompt Refinement (Option B) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four structural prompt bugs, separate analysis context from generation style, and add a `style_preset` dropdown + `style_notes` override field to `AudioMoodAnalyzer`.

**Architecture:** Single-file change (`audio_mood_analyzer.py`). Add a module-level `STYLE_PRESETS` dict and `_build_style_block()` helper. Thread `style_block` through the three generation prompt builders; restrict `custom_context` to the two analysis prompt builders. Fix indentation, conditional fields, and the empty-subject merge edge case.

**Tech Stack:** Python 3.x, no new dependencies.

---

## File map

| File | Action |
|------|--------|
| `audio_mood_analyzer.py` | Modify — all changes land here |
| `tests/test_prompts.py` | Create — unit tests for pure functions (no Ollama needed) |

---

### Task 1: Fix structural bugs in existing prompts

No new inputs yet. Fix the four issues identified in the spec before adding anything new.

**Files:**
- Modify: `audio_mood_analyzer.py`

- [ ] **Step 1.1: Fix indentation in `_build_environment_prompt_request`**

The entire prompt body currently has 4-space leading indentation (f-string is indented with the method body). Replace the method with one whose content starts at column 0:

```python
def _build_environment_prompt_request(self, mood_json, subject_json, custom_context):
    return f"""
You are an art director creating an environment-only image-generation prompt.

Use the sonic mood analysis as the main source:
{_fmt_json(mood_json)}

Use the lyrical subject analysis only as subtle atmospheric influence:
{_fmt_json(subject_json)}

Additional creative context:
{custom_context}

Create a prompt for the ENVIRONMENT ONLY.
No people.
No human subjects.
No portraits.

Focus on:
- location
- atmosphere
- darkness
- lighting
- color palette
- spatial pressure
- painterly texture
- emotional landscape
- composition
- visual rhythm

Avoid:
- literal illustration of the lyrics
- generic masterpiece tags
- glossy AI look
- literal horror clichés

Output only the final image-generation prompt.
"""
```

- [ ] **Step 1.2: Fix indentation in `_build_subject_analysis_prompt`**

Same issue — 4-space prefix on every line. Replace with column-0 content. Also move the JSON instruction to the final line:

```python
def _build_subject_analysis_prompt(
    self,
    lyrics_or_text,
    focus_fragment,
    song_title,
    custom_context,
    song_description="",
    song_genre="",
):
    title_line = f"\nSong title:\n{song_title}" if song_title.strip() else ""
    genre_line = f"\nGenre / style:\n{song_genre}" if song_genre.strip() else ""
    description_block = (
        f"\nSong description (general meaning, emotional arc, artist intent):\n{song_description}"
        if song_description.strip() else ""
    )
    return f"""
You are an art director analyzing lyrics or poetic text to extract the HUMAN SUBJECT.

Do not summarize the lyrics.
Do not quote the lyrics.
Do not copy lines from the lyrics.

Your goal is to infer a visually renderable human subject from emotional and symbolic material.

Additional creative context:
{custom_context}
{title_line}{genre_line}{description_block}

Full lyrics or source text:
{lyrics_or_text}

Focus fragment:
{focus_fragment}

Use the song title, genre, and description as thematic and symbolic context.
The focus fragment is the PRIMARY emotional and visual anchor.
Use the rest of the lyrics only as secondary atmospheric context.

If the source text is written in first person,
translate it into third-person visual language.

Do not preserve the original point of view.

Convert internal emotions into visible external characteristics:
- posture
- expression
- gaze
- body tension
- movement
- symbolic attributes
- emotional pressure
- vulnerability
- psychological instability

Return only valid JSON with this structure:
{{
  "narrative_voice": "",
  "subject_role": "",
  "third_person_subject_description": "",
  "subject_psychology": [],
  "emotional_conflict": [],
  "posture": [],
  "expression": [],
  "eyes_and_face": [],
  "body_language": [],
  "symbolic_attributes": [],
  "implied_motion": [],
  "visible_translation_of_inner_state": [],
  "visual_distortions": [],
  "avoid": []
}}

Focus on emotional specificity rather than generic symbolism.

The final subject should feel visually concrete, emotionally vulnerable,
psychologically believable, and suitable for painterly image generation.

Do not include any text before or after the JSON.
"""
```

Note: `song_title` is now conditionally injected (same pattern as `song_description`/`song_genre`). The old always-printed `Song title:` header is gone.

- [ ] **Step 1.3: Move JSON instruction to final line in `_build_mood_prompt`**

The current prompt ends with "Do not quote the song." Move the JSON schema to the very end with a final "Do not include any text before or after the JSON." line:

```python
def _build_mood_prompt(self, features, custom_context):
    return f"""
You are an art director analyzing music as pure sound.

Do not use lyrics.
Do not infer meaning from words.
Analyze only the sonic features described below:
tempo, dynamics, energy, density, brightness, darkness, rhythm, tension,
loudness changes, and instrumental pressure.

Additional creative context:
{custom_context}

Audio features:
{_fmt_json(features)}

Transform these audio features into a visual mood sheet for image generation.

Focus on atmosphere, intensity, movement, emotional pressure, vulnerability,
darkness, contrast, rhythm and painterly interpretation.

Do not mention lyrics.
Do not quote the song.

Return only valid JSON with this structure:
{{
  "sonic_mood": [],
  "energy_profile": "",
  "tension_profile": "",
  "visual_environment_implications": [],
  "lighting_implications": [],
  "color_palette": [],
  "texture_implications": [],
  "subject_presence": [],
  "composition_suggestions": [],
  "motion_feel": [],
  "camera_language": [],
  "avoid": []
}}

Do not include any text before or after the JSON.
"""
```

- [ ] **Step 1.4: Fix empty `subject_prompt` in `_build_merge_prompt_request`**

When no lyrics are provided, `subject_prompt` is `""`. The merge prompt currently includes "Subject prompt:" with an empty value. Detect this and switch framing:

```python
def _build_merge_prompt_request(
    self,
    mood_json,
    environment_prompt,
    subject_prompt,
    custom_context,
):
    if subject_prompt.strip():
        subject_section = f"\nSubject prompt:\n{subject_prompt}\n"
        task_instruction = (
            "Merge the environment and subject into one coherent final image-generation prompt."
        )
    else:
        subject_section = ""
        task_instruction = (
            "Refine and elevate the environment prompt into a final image-generation prompt. "
            "No human subject is present — keep the focus on atmosphere, landscape, and mood."
        )

    return f"""
You are an art director composing a final image-generation prompt.

Sonic mood analysis:
{_fmt_json(mood_json)}

Environment prompt:
{environment_prompt}
{subject_section}
Additional creative context:
{custom_context}

{task_instruction}

Keep it:
- coherent
- painterly
- emotional
- atmospheric
- symbolic
- visually specific
- suitable for image generation

Avoid:
- generic masterpiece tags
- glossy AI look
- repetitive adjectives
- literal horror clichés
- excessive camera jargon
- overdescribing

Output only the final image-generation prompt.
"""
```

- [ ] **Step 1.5: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 1.6: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "fix: prompt indentation, song_title conditional, mood JSON instruction order, empty-subject merge handling"
```

---

### Task 2: Add `STYLE_PRESETS` constant and `_build_style_block()` helper

**Files:**
- Modify: `audio_mood_analyzer.py`
- Create: `tests/test_prompts.py`

- [ ] **Step 2.1: Write failing tests for `_build_style_block`**

Create `tests/test_prompts.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from audio_mood_analyzer import _build_style_block

def test_known_preset_returns_preset_text():
    result = _build_style_block("painterly", "")
    assert "Francis Bacon" in result
    assert result.strip()

def test_preset_plus_notes_appends_notes():
    result = _build_style_block("painterly", "cold palette, morning light")
    assert "Francis Bacon" in result
    assert "cold palette, morning light" in result

def test_custom_preset_empty_notes_returns_empty():
    result = _build_style_block("custom", "")
    assert result == ""

def test_custom_preset_with_notes_returns_notes_only():
    result = _build_style_block("custom", "my own direction")
    assert result == "my own direction"
    assert "Francis Bacon" not in result

def test_unknown_preset_falls_back_to_empty():
    result = _build_style_block("nonexistent", "")
    assert result == ""
```

- [ ] **Step 2.2: Run tests — expect failure**

```bash
python3 -m pytest tests/test_prompts.py -v
```

Expected: `ImportError` or `NameError` — `_build_style_block` does not exist yet.

- [ ] **Step 2.3: Add `STYLE_PRESETS` and `_build_style_block` to `audio_mood_analyzer.py`**

Add immediately after the `_LOG = "[AudioMoodAnalyzer]"` line:

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


def _build_style_block(style_preset: str, style_notes: str) -> str:
    base = STYLE_PRESETS.get(style_preset, "")
    notes = style_notes.strip()
    if base and notes:
        return f"{base}\n{notes}"
    return notes if notes else base
```

- [ ] **Step 2.4: Run tests — expect pass**

```bash
python3 -m pytest tests/test_prompts.py -v
```

Expected: all 5 tests `PASSED`.

- [ ] **Step 2.5: Commit**

```bash
git add audio_mood_analyzer.py tests/test_prompts.py
git commit -m "feat: add STYLE_PRESETS and _build_style_block helper with tests"
```

---

### Task 3: Add `style_preset` and `style_notes` inputs to the node

**Files:**
- Modify: `audio_mood_analyzer.py`

- [ ] **Step 3.1: Add inputs to `INPUT_TYPES`**

In `INPUT_TYPES`, after `song_genre` and before `generate_environment_prompt`, add:

```python
"style_preset": (
    ["painterly", "cinematic", "raw", "abstract", "custom"],
    {"default": "painterly"}
),
"style_notes": ("STRING", {
    "multiline": True,
    "default": ""
}),
```

- [ ] **Step 3.2: Add parameters to `analyze()`**

In the `analyze()` method signature, after `song_genre` and before `generate_environment_prompt`:

```python
style_preset,
style_notes,
```

- [ ] **Step 3.3: Compute `style_block` at the top of `analyze()`**

After the `print(f"{_LOG} audio: ...")` line, add:

```python
style_block = _build_style_block(style_preset, style_notes)
```

- [ ] **Step 3.4: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3.5: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat: add style_preset and style_notes inputs; compute style_block in analyze()"
```

---

### Task 4: Inject `style_block` into generation prompts; remove `custom_context` from them

`custom_context` stays in the two **analysis** prompts. It is removed from the three **generation** prompts, which receive `style_block` instead.

**Files:**
- Modify: `audio_mood_analyzer.py`

- [ ] **Step 4.1: Update `_build_environment_prompt_request` signature and body**

Replace the method:

```python
def _build_environment_prompt_request(self, mood_json, subject_json, style_block):
    style_section = f"\nVisual style target:\n{style_block}\n" if style_block.strip() else ""
    return f"""
You are an art director creating an environment-only image-generation prompt.
{style_section}
Use the sonic mood analysis as the main source:
{_fmt_json(mood_json)}

Use the lyrical subject analysis only as subtle atmospheric influence:
{_fmt_json(subject_json)}

Create a prompt for the ENVIRONMENT ONLY.
No people.
No human subjects.
No portraits.

Focus on:
- location
- atmosphere
- darkness
- lighting
- color palette
- spatial pressure
- painterly texture
- emotional landscape
- composition
- visual rhythm

Avoid:
- literal illustration of the lyrics
- generic masterpiece tags
- glossy AI look
- literal horror clichés

Output only the final image-generation prompt.
"""
```

- [ ] **Step 4.2: Update `_build_subject_prompt_request` signature and body**

Replace the method:

```python
def _build_subject_prompt_request(self, subject_json, style_block):
    style_section = f"\nVisual style target:\n{style_block}\n" if style_block.strip() else ""
    return f"""
You are an art director creating a subject-only image-generation prompt.
{style_section}
Use the following subject analysis extracted from lyrics or poetic text:
{_fmt_json(subject_json)}

Create a prompt for the HUMAN SUBJECT ONLY.
Use a minimal or neutral background.

Focus on:
- posture
- expression
- emotional state
- body tension
- face and eyes
- vulnerability
- subtle distortion
- symbolic attributes
- painterly texture
- psychological pressure

Avoid:
- generic beauty portrait
- glossy AI look
- perfect anatomy obsession
- literal horror clichés
- overdescribing

If the source text is written in first person,
translate it into third-person visual language.
Do not preserve the original point of view.
Convert "I" into "a solitary figure", "the subject", "a person", or a more specific visual archetype.
Focus on what can be seen externally: posture, expression, gesture, tension, gaze, movement, symbolic attributes.

Output only the final image-generation prompt.
"""
```

- [ ] **Step 4.3: Update `_build_merge_prompt_request` signature and body**

Replace the method (note: receives `summary` string instead of full `mood_json`):

```python
def _build_merge_prompt_request(
    self,
    mood_summary,
    environment_prompt,
    subject_prompt,
    style_block,
):
    style_section = f"\nVisual style target:\n{style_block}\n" if style_block.strip() else ""
    if subject_prompt.strip():
        subject_section = f"\nSubject prompt:\n{subject_prompt}\n"
        task_instruction = (
            "Merge the environment and subject into one coherent final image-generation prompt."
        )
    else:
        subject_section = ""
        task_instruction = (
            "Refine and elevate the environment prompt into a final image-generation prompt. "
            "No human subject is present — keep the focus on atmosphere, landscape, and mood."
        )

    return f"""
You are an art director composing a final image-generation prompt.
{style_section}
Sonic mood summary:
{mood_summary}

Environment prompt:
{environment_prompt}
{subject_section}
{task_instruction}

Keep it:
- coherent
- emotional
- atmospheric
- symbolic
- visually specific
- suitable for image generation

Avoid:
- generic masterpiece tags
- glossy AI look
- repetitive adjectives
- literal horror clichés
- excessive camera jargon
- overdescribing

Output only the final image-generation prompt.
"""
```

- [ ] **Step 4.4: Verify syntax**

```bash
python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 4.5: Commit**

```bash
git add audio_mood_analyzer.py
git commit -m "refactor: inject style_block into generation prompts; remove custom_context from generation phase"
```

---

### Task 5: Wire `style_block` and updated signatures in `analyze()`

Update every call-site in `analyze()` to match the new method signatures.

**Files:**
- Modify: `audio_mood_analyzer.py`

- [ ] **Step 5.1: Update the environment prompt call**

Find:
```python
self._build_environment_prompt_request(
    mood_json=mood_json,
    subject_json=subject_json,
    custom_context=custom_context,
),
```

Replace with:
```python
self._build_environment_prompt_request(
    mood_json=mood_json,
    subject_json=subject_json,
    style_block=style_block,
),
```

- [ ] **Step 5.2: Update the subject prompt call**

Find:
```python
self._build_subject_prompt_request(
    subject_json=subject_json,
    custom_context=custom_context,
),
```

Replace with:
```python
self._build_subject_prompt_request(
    subject_json=subject_json,
    style_block=style_block,
),
```

- [ ] **Step 5.3: Update the merge prompt call**

Find:
```python
self._build_merge_prompt_request(
    mood_json=mood_json,
    environment_prompt=environment_prompt,
    subject_prompt=subject_prompt,
    custom_context=custom_context,
),
```

Replace with:
```python
self._build_merge_prompt_request(
    mood_summary=summary,
    environment_prompt=environment_prompt,
    subject_prompt=subject_prompt,
    style_block=style_block,
),
```

Note: `summary` is already computed earlier in `analyze()` via `self._build_summary(mood_json)`.

- [ ] **Step 5.4: Verify syntax and run tests**

```bash
python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
python3 -m pytest tests/test_prompts.py -v
```

Expected: `OK` and all tests `PASSED`.

- [ ] **Step 5.5: Final commit**

```bash
git add audio_mood_analyzer.py
git commit -m "feat: wire style_block through analyze(); pass summary to merge prompt"
```

---

## Self-review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Fix 4-space indentation in environment prompt | Task 1.1 |
| Fix 4-space indentation in subject analysis prompt | Task 1.2 |
| Conditional song_title injection | Task 1.2 |
| Move JSON-only instruction to final line | Tasks 1.2, 1.3 |
| Fix empty subject_prompt in merge | Task 1.4 |
| `STYLE_PRESETS` dict | Task 2.3 |
| `_build_style_block()` helper | Task 2.3 |
| Tests for `_build_style_block` | Task 2.1 |
| `style_preset` dropdown input | Task 3.1 |
| `style_notes` text input | Task 3.1 |
| `style_block` computed once in `analyze()` | Task 3.3 |
| `style_block` injected into environment prompt | Task 4.1 |
| `style_block` injected into subject prompt | Task 4.2 |
| `style_block` injected into merge prompt | Task 4.3 |
| `custom_context` removed from generation prompts | Tasks 4.1–4.3 |
| Empty style_block omits "Visual style target:" section | Tasks 4.1–4.3 (conditional) |
| `summary` passed to merge instead of full `mood_json` | Tasks 4.3, 5.3 |
| Empty subject_prompt → "refine" framing | Tasks 1.4, 4.3 |

All spec requirements covered. No placeholders.
