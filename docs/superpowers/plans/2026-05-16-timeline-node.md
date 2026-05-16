# AudioMoodAnalyzerTimeline — Implementation Plan (T-005)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `AudioMoodAnalyzerTimeline`, a new ComfyUI node that divides audio into N equal segments and runs the full mood analysis + prompt generation pipeline on each, returning a JSON sequence and newline-separated prompt strings for image-sequence and video workflows.

**Architecture:** Single new class in `audio_mood_analyzer.py`, inheriting from `AudioMoodAnalyzer`. Adds one input (`n_segments`), overrides `RETURN_TYPES`/`FUNCTION`, and implements `analyze_timeline()` which runs subject analysis once and loops over segments for mood + generation calls. Does NOT call `super().analyze()`. Sample workflow saved to `example_workflow/example_timeline.json`.

**Tech Stack:** Python 3.x, librosa, requests, numpy (all existing). No new dependencies.

**Prerequisite:** Option B complete — `_build_style_block`, `STYLE_PRESETS`, and all `_build_*` prompt methods must exist on `AudioMoodAnalyzer`.

---

## File map

| File | Action |
|------|--------|
| `audio_mood_analyzer.py` | Modify — add `AudioMoodAnalyzerTimeline` class and update registrations |
| `tests/test_timeline_node.py` | Create — unit tests for skeleton and analyze_timeline() |
| `example_workflow/example_timeline.json` | Create — sample workflow demonstrating the node |

---

### Task 1: Class skeleton — INPUT_TYPES, RETURN_TYPES, registration

**Files:**
- Modify: `audio_mood_analyzer.py`
- Create: `tests/test_timeline_node.py`

- [ ] **Step 1.1: Write failing tests for the skeleton**

Create `tests/test_timeline_node.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from audio_mood_analyzer import AudioMoodAnalyzerTimeline


def test_timeline_node_exists():
    node = AudioMoodAnalyzerTimeline()
    assert node is not None


def test_input_types_has_n_segments():
    inputs = AudioMoodAnalyzerTimeline.INPUT_TYPES()
    assert "n_segments" in inputs["required"]


def test_n_segments_default_is_8():
    inputs = AudioMoodAnalyzerTimeline.INPUT_TYPES()
    _, meta = inputs["required"]["n_segments"]
    assert meta["default"] == 8


def test_n_segments_inserted_before_generate_booleans():
    inputs = AudioMoodAnalyzerTimeline.INPUT_TYPES()
    keys = list(inputs["required"].keys())
    assert keys.index("n_segments") < keys.index("generate_environment_prompt")


def test_return_types_count_is_4():
    assert len(AudioMoodAnalyzerTimeline.RETURN_TYPES) == 4


def test_return_names_are_correct():
    assert AudioMoodAnalyzerTimeline.RETURN_NAMES == (
        "prompt_sequence_json", "merge_prompts", "environment_prompts", "subject_prompt"
    )
```

- [ ] **Step 1.2: Run tests — expect ImportError**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/test_timeline_node.py -v 2>&1 | tail -8
```

Expected: `ImportError: cannot import name 'AudioMoodAnalyzerTimeline'`

- [ ] **Step 1.3: Add the class skeleton to `audio_mood_analyzer.py`**

Insert before `NODE_CLASS_MAPPINGS` (after `AudioMoodAnalyzerAdvanced`):

```python
class AudioMoodAnalyzerTimeline(AudioMoodAnalyzer):

    @classmethod
    def INPUT_TYPES(cls):
        parent = super().INPUT_TYPES()
        required = {}
        for k, v in parent["required"].items():
            if k == "generate_environment_prompt":
                required["n_segments"] = ("INT", {
                    "default": 8, "min": 2, "max": 32, "step": 1
                })
            required[k] = v
        parent["required"] = required
        return parent

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt_sequence_json", "merge_prompts", "environment_prompts", "subject_prompt")
    FUNCTION = "analyze_timeline"
    CATEGORY = "audio/analysis"
```

- [ ] **Step 1.4: Update `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`**

```python
NODE_CLASS_MAPPINGS = {
    "AudioMoodAnalyzer": AudioMoodAnalyzer,
    "AudioMoodAnalyzerAdvanced": AudioMoodAnalyzerAdvanced,
    "AudioMoodAnalyzerTimeline": AudioMoodAnalyzerTimeline,
    "OllamaModelSelector": OllamaModelSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioMoodAnalyzer": "Audio Mood Analyzer",
    "AudioMoodAnalyzerAdvanced": "Audio Mood Analyzer (Advanced)",
    "AudioMoodAnalyzerTimeline": "Audio Mood Analyzer (Timeline)",
    "OllamaModelSelector": "Ollama Model Selector",
}
```

- [ ] **Step 1.5: Run tests — all 6 should pass**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/test_timeline_node.py -v
```

Expected: 6/6 PASSED.

- [ ] **Step 1.6: Verify syntax**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 1.7: Commit**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && git add audio_mood_analyzer.py tests/test_timeline_node.py && git commit -m "feat: add AudioMoodAnalyzerTimeline skeleton with INPUT_TYPES and registration"
```

---

### Task 2: Implement `analyze_timeline()`

**Files:**
- Modify: `audio_mood_analyzer.py`
- Modify: `tests/test_timeline_node.py`

- [ ] **Step 2.1: Add failing tests for `analyze_timeline()`**

Append to `tests/test_timeline_node.py`:

```python
import json
import numpy as np
from unittest.mock import patch

MOCK_MOOD_JSON_STR = json.dumps({
    "sonic_mood": ["dark"], "energy_profile": "high", "tension_profile": "rising",
    "visual_environment_implications": [], "lighting_implications": [],
    "color_palette": [], "texture_implications": [], "subject_presence": [],
    "composition_suggestions": [], "motion_feel": [], "camera_language": [], "avoid": []
})

MOCK_SUBJECT_JSON_STR = json.dumps({
    "narrative_voice": "first", "subject_role": "student",
    "third_person_subject_description": "a solitary figure",
    "subject_psychology": [], "emotional_conflict": [], "posture": [],
    "expression": [], "eyes_and_face": [], "body_language": [],
    "symbolic_attributes": [], "implied_motion": [],
    "visible_translation_of_inner_state": [], "visual_distortions": [], "avoid": []
})

DUMMY_FEATURES = {
    "duration_seconds": 4.5, "tempo_bpm": 120.0, "beat_count": 10,
    "rms_energy_mean": 0.0, "rms_energy_max": 0.0, "rms_energy_min": 0.0,
    "dynamic_range": 0.0, "brightness_mean_spectral_centroid": 0.0,
    "brightness_max_spectral_centroid": 0.0, "spectral_bandwidth_mean": 0.0,
    "zero_crossing_rate_mean": 0.0, "onset_strength_mean": 0.0,
    "onset_strength_max": 0.0, "energy_sections": []
}

DUMMY_Y = np.zeros(44100 * 18, dtype=np.float32)  # 18 seconds

CALL_COUNTER = {}

def fake_timed_generate(label, ollama_url, model, prompt, temperature, num_predict=-1):
    CALL_COUNTER[label] = CALL_COUNTER.get(label, 0) + 1
    if "mood analysis" in label:
        return MOCK_MOOD_JSON_STR
    if "subject analysis" in label:
        return MOCK_SUBJECT_JSON_STR
    if "subject prompt" in label:
        return "a solitary figure in shadows"
    if "environment prompt" in label:
        return "dark crumbling wasteland"
    if "merge prompt" in label:
        return f"unified prompt {CALL_COUNTER[label]}"
    return ""


def run_timeline(n_segments=4, lyrics="some lyrics", generate_subject_prompt=True):
    CALL_COUNTER.clear()
    node = AudioMoodAnalyzerTimeline()
    with patch.object(node, "_timed_generate", side_effect=fake_timed_generate), \
         patch.object(node, "_audio_to_numpy", return_value=(DUMMY_Y, 44100)), \
         patch.object(node, "_extract_features", return_value=DUMMY_FEATURES):
        return node.analyze_timeline(
            audio={},
            ollama_url="http://localhost:11434/api/generate",
            model="test",
            analysis_temperature=0.4,
            prompt_temperature=0.8,
            custom_context="ctx",
            lyrics_or_text=lyrics,
            focus_fragment="",
            song_title="",
            song_description="",
            song_genre="",
            style_preset="painterly",
            style_notes="",
            n_segments=n_segments,
            generate_environment_prompt=True,
            generate_subject_prompt=generate_subject_prompt,
            generate_merge_prompt=True,
        )


def test_analyze_timeline_returns_4_outputs():
    result = run_timeline(n_segments=4)
    assert len(result) == 4


def test_prompt_sequence_json_has_correct_segment_count():
    seq_json, _, _, _ = run_timeline(n_segments=4)
    segments = json.loads(seq_json)
    assert len(segments) == 4


def test_segment_schema_has_required_fields():
    seq_json, _, _, _ = run_timeline(n_segments=2)
    segments = json.loads(seq_json)
    for seg in segments:
        assert "segment" in seg
        assert "start_s" in seg
        assert "end_s" in seg
        assert "mood_json" in seg
        assert "environment_prompt" in seg
        assert "subject_prompt" in seg
        assert "merge_prompt" in seg


def test_segment_numbers_are_1_indexed():
    seq_json, _, _, _ = run_timeline(n_segments=3)
    segments = json.loads(seq_json)
    assert [s["segment"] for s in segments] == [1, 2, 3]


def test_segment_times_are_monotonic():
    seq_json, _, _, _ = run_timeline(n_segments=4)
    segments = json.loads(seq_json)
    for seg in segments:
        assert seg["start_s"] < seg["end_s"]
    for i in range(len(segments) - 1):
        assert segments[i]["end_s"] <= segments[i + 1]["start_s"]


def test_merge_prompts_has_n_lines():
    _, merge_prompts, _, _ = run_timeline(n_segments=4)
    lines = [l for l in merge_prompts.split("\n") if l.strip()]
    assert len(lines) == 4


def test_environment_prompts_has_n_lines():
    _, _, env_prompts, _ = run_timeline(n_segments=4)
    lines = [l for l in env_prompts.split("\n") if l.strip()]
    assert len(lines) == 4


def test_subject_prompt_is_single_string():
    _, _, _, subject_prompt = run_timeline(n_segments=4)
    assert isinstance(subject_prompt, str)
    assert "\n" not in subject_prompt or subject_prompt == ""


def test_no_lyrics_gives_empty_subject_prompt():
    _, _, _, subject_prompt = run_timeline(n_segments=2, lyrics="")
    assert subject_prompt == ""


def test_subject_prompt_repeated_in_each_segment():
    seq_json, _, _, subject_prompt = run_timeline(n_segments=3, lyrics="some lyrics")
    if subject_prompt:
        segments = json.loads(seq_json)
        for seg in segments:
            assert seg["subject_prompt"] == subject_prompt
```

- [ ] **Step 2.2: Run tests — expect failures**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/test_timeline_node.py -v 2>&1 | tail -15
```

Expected: the 6 skeleton tests PASS; the 10 new tests FAIL with `AttributeError: 'AudioMoodAnalyzerTimeline' object has no attribute 'analyze_timeline'`.

- [ ] **Step 2.3: Implement `analyze_timeline()` inside `AudioMoodAnalyzerTimeline`**

Add this method to the class (after the `INPUT_TYPES` classmethod):

```python
def analyze_timeline(
    self,
    audio,
    ollama_url,
    model,
    analysis_temperature,
    prompt_temperature,
    custom_context,
    lyrics_or_text,
    focus_fragment,
    song_title,
    song_description,
    song_genre,
    style_preset,
    style_notes,
    n_segments,
    generate_environment_prompt,
    generate_subject_prompt,
    generate_merge_prompt,
):
    t0 = time.time()
    y, sr = self._audio_to_numpy(audio)
    style_block = _build_style_block(style_preset, style_notes)
    total_samples = len(y)
    seg_samples = total_samples // n_segments

    print(f"{_LOG} timeline: {n_segments} segments  "
          f"{round(total_samples / sr, 1)}s  model: {model}")

    # Subject analysis — once, shared across all segments
    subject_json = {}
    subject_prompt_str = ""
    has_subject_data = (
        lyrics_or_text.strip() or focus_fragment.strip() or song_title.strip()
        or song_description.strip() or song_genre.strip()
    )
    if has_subject_data:
        raw_subject = self._timed_generate(
            "subject analysis", ollama_url, model,
            self._build_subject_analysis_prompt(
                lyrics_or_text=lyrics_or_text,
                focus_fragment=focus_fragment,
                song_title=song_title,
                custom_context=custom_context,
                song_description=song_description,
                song_genre=song_genre,
            ),
            analysis_temperature,
        )
        subject_json = self._extract_json(raw_subject)
        if generate_subject_prompt and subject_json and "error" not in subject_json:
            subject_prompt_str = self._timed_generate(
                "subject prompt", ollama_url, model,
                self._build_subject_prompt_request(subject_json, style_block),
                prompt_temperature,
            )

    segments = []
    for i in range(n_segments):
        start = i * seg_samples
        end = (i + 1) * seg_samples if i < n_segments - 1 else total_samples
        y_seg = y[start:end]
        start_s = round(start / sr, 2)
        end_s = round(end / sr, 2)

        features = self._extract_features(y_seg, sr)

        raw_mood = self._timed_generate(
            f"mood analysis [seg {i + 1}/{n_segments}]", ollama_url, model,
            self._build_mood_prompt(features, custom_context),
            analysis_temperature,
        )
        mood_json = self._extract_json(raw_mood)
        mood_summary = self._build_summary(mood_json)

        environment_prompt = ""
        if generate_environment_prompt:
            try:
                environment_prompt = self._timed_generate(
                    f"environment prompt [seg {i + 1}/{n_segments}]", ollama_url, model,
                    self._build_environment_prompt_request(mood_json, subject_json, style_block),
                    prompt_temperature,
                )
            except Exception as exc:
                print(f"{_LOG} ⚠ environment prompt seg {i + 1} failed: {exc}")

        merge_prompt = ""
        if generate_merge_prompt:
            try:
                merge_prompt = self._timed_generate(
                    f"merge prompt [seg {i + 1}/{n_segments}]", ollama_url, model,
                    self._build_merge_prompt_request(
                        mood_summary, environment_prompt, subject_prompt_str, style_block
                    ),
                    prompt_temperature,
                )
            except Exception as exc:
                print(f"{_LOG} ⚠ merge prompt seg {i + 1} failed: {exc}")

        segments.append({
            "segment": i + 1,
            "start_s": start_s,
            "end_s": end_s,
            "mood_json": mood_json,
            "environment_prompt": environment_prompt,
            "subject_prompt": subject_prompt_str,
            "merge_prompt": merge_prompt,
        })

    print(f"{_LOG} timeline done  total: {time.time() - t0:.1f}s")

    return (
        json.dumps(segments, indent=2, ensure_ascii=False),
        "\n".join(s["merge_prompt"] for s in segments),
        "\n".join(s["environment_prompt"] for s in segments),
        subject_prompt_str,
    )
```

- [ ] **Step 2.4: Run all tests — expect all pass**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/ -v 2>&1 | tail -25
```

Expected: all 27 tests PASSED (16 existing + 6 skeleton + 10 analyze_timeline + the extra `test_subject_prompt_repeated_in_each_segment` = actually 16 + 16 = let's count: 5 ollama, 11 advanced, 5 prompts, 6 skeleton, 10 new = 37... wait, let me recount.

Current test count before this task:
- test_prompts.py: 5
- test_advanced_node.py: 6
- test_ollama_selector.py: 5
Total existing: 16

New tests this task:
- Skeleton tests (already added in Task 1): 6
- analyze_timeline tests: 11 (the 10 listed + test_subject_prompt_repeated)
Total new: 17

Grand total: 33 tests. Expected: all 33 PASSED.

- [ ] **Step 2.5: Verify syntax**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 2.6: Commit**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && git add audio_mood_analyzer.py tests/test_timeline_node.py && git commit -m "feat: implement AudioMoodAnalyzerTimeline.analyze_timeline() with tests"
```

---

### Task 3: Sample workflow and README update

**Files:**
- Create: `example_workflow/example_timeline.json`
- Modify: `README.md`

- [ ] **Step 3.1: Create `example_workflow/example_timeline.json`**

Write this exact file:

```json
{
  "id": "timeline-example-001",
  "revision": 0,
  "last_node_id": 20,
  "last_link_id": 20,
  "nodes": [
    {
      "id": 1,
      "type": "UNETLoader",
      "pos": [471, 100],
      "size": [412, 110],
      "flags": {},
      "order": 2,
      "mode": 0,
      "inputs": [],
      "outputs": [{"name": "MODEL", "type": "MODEL", "links": [1]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "UNETLoader"},
      "widgets_values": ["zImageTurbo_turbo.safetensors", "default"],
      "color": "#432",
      "bgcolor": "#653"
    },
    {
      "id": 2,
      "type": "CLIPLoader",
      "pos": [478, 265],
      "size": [416, 179],
      "flags": {},
      "order": 3,
      "mode": 0,
      "inputs": [],
      "outputs": [{"name": "CLIP", "type": "CLIP", "links": [2]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "CLIPLoader"},
      "widgets_values": ["qwen_3_4b.safetensors", "lumina2", "default"],
      "color": "#432",
      "bgcolor": "#653"
    },
    {
      "id": 3,
      "type": "VAELoader",
      "pos": [465, 515],
      "size": [418, 82],
      "flags": {},
      "order": 0,
      "mode": 0,
      "inputs": [],
      "outputs": [{"name": "VAE", "type": "VAE", "links": [3]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "VAELoader"},
      "widgets_values": ["ae.safetensors"],
      "color": "#432",
      "bgcolor": "#653"
    },
    {
      "id": 4,
      "type": "LoraLoader",
      "pos": [967, -53],
      "size": [462, 170],
      "flags": {},
      "order": 5,
      "mode": 4,
      "inputs": [
        {"name": "model", "type": "MODEL", "link": 1},
        {"name": "clip", "type": "CLIP", "link": 2}
      ],
      "outputs": [
        {"name": "MODEL", "type": "MODEL", "links": [4]},
        {"name": "CLIP", "type": "CLIP", "links": [5, 6]}
      ],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.1", "Node name for S&R": "LoraLoader"},
      "widgets_values": ["fear_of_the_art/C76QWWBWVH39DTSM9EQFG55XM0.safetensors", 1, 1],
      "color": "#2a363b",
      "bgcolor": "#3f5159"
    },
    {
      "id": 5,
      "type": "EmptySD3LatentImage",
      "pos": [1040, 790],
      "size": [410, 188],
      "flags": {},
      "order": 1,
      "mode": 0,
      "inputs": [],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [7]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "EmptySD3LatentImage"},
      "widgets_values": [1200, 848, 1],
      "color": "#332922",
      "bgcolor": "#593930"
    },
    {
      "id": 6,
      "type": "LoadAudio",
      "pos": [-2398, 35],
      "size": [441, 269],
      "flags": {},
      "order": 4,
      "mode": 0,
      "inputs": [],
      "outputs": [{"name": "AUDIO", "type": "AUDIO", "links": [8]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "LoadAudio"},
      "widgets_values": ["Pearl Jam - Jeremy (Official 4K Video).mp3", null, null]
    },
    {
      "id": 7,
      "type": "FL_Audio_Crop",
      "pos": [-1920, 55],
      "size": [270, 82],
      "flags": {},
      "order": 6,
      "mode": 0,
      "inputs": [{"name": "audio", "type": "AUDIO", "link": 8}],
      "outputs": [{"name": "audio", "type": "AUDIO", "links": [9, 10]}],
      "properties": {"cnr_id": "comfyui_fearnworksnodes", "ver": "0.1.2", "Node name for S&R": "FL_Audio_Crop"},
      "widgets_values": ["0:39", "0:57"],
      "color": "#16727c",
      "bgcolor": "#4F0074"
    },
    {
      "id": 8,
      "type": "PreviewAudio",
      "pos": [-1600, -83],
      "size": [270, 88],
      "flags": {},
      "order": 9,
      "mode": 0,
      "inputs": [{"name": "audio", "type": "AUDIO", "link": 9}],
      "outputs": [],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.1", "Node name for S&R": "PreviewAudio"},
      "widgets_values": []
    },
    {
      "id": 9,
      "type": "OllamaModelSelector",
      "pos": [-1918, 220],
      "size": [270, 58],
      "flags": {},
      "order": 7,
      "mode": 0,
      "inputs": [],
      "outputs": [
        {"name": "models_list", "type": "STRING", "links": [11]},
        {"name": "first_model", "type": "STRING", "links": null}
      ],
      "properties": {"cnr_id": "comfyui_fearnworksnodes", "Node name for S&R": "OllamaModelSelector"},
      "widgets_values": ["http://localhost:11434"]
    },
    {
      "id": 10,
      "type": "PreviewAny",
      "pos": [-1600, 220],
      "size": [380, 160],
      "flags": {},
      "order": 10,
      "mode": 0,
      "inputs": [{"name": "source", "type": "*", "link": 11}],
      "outputs": [{"name": "STRING", "type": "STRING", "links": null}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "PreviewAny"},
      "widgets_values": [null, null, null]
    },
    {
      "id": 11,
      "type": "AudioMoodAnalyzerTimeline",
      "pos": [-1286, 122],
      "size": [576, 870],
      "flags": {},
      "order": 8,
      "mode": 0,
      "inputs": [{"name": "audio", "type": "AUDIO", "link": 10}],
      "outputs": [
        {"name": "prompt_sequence_json", "type": "STRING", "links": [12]},
        {"name": "merge_prompts", "type": "STRING", "links": [13]},
        {"name": "environment_prompts", "type": "STRING", "links": [15]},
        {"name": "subject_prompt", "type": "STRING", "links": [16]}
      ],
      "properties": {"cnr_id": "comfyui_fearnworksnodes", "Node name for S&R": "AudioMoodAnalyzerTimeline"},
      "widgets_values": [
        "http://localhost:11434/api/generate",
        "hf.co/unsloth/Qwen3-4B-Instruct-2507-GGUF:UD-Q4_K_XL",
        0.6,
        0.8,
        "Analyze the music as pure sound, not lyrics. Translate sonic qualities into emotional visual direction.",
        "At home Drawing pictures Of mountain tops With him on top Lemon yellow sun\nArms raised in a V\nThe dead lay in pools of maroon below",
        "pictures Of mountain With him on",
        "Jeremy",
        "\"Jeremy\" is a 1992 Pearl Jam song inspired by the true story of Jeremy Wade Delle, a 15-year-old Texan boy who died by suicide on January 8, 1991, in front of his English class at Richardson High School. The song addresses themes of teenage bullying, neglect, and alienation.",
        "rock, grunge",
        "raw",
        "",
        8,
        true,
        true,
        true
      ]
    },
    {
      "id": 12,
      "type": "PreviewAny",
      "pos": [-763, -526],
      "size": [421, 420],
      "flags": {},
      "order": 11,
      "mode": 0,
      "inputs": [{"name": "source", "type": "*", "link": 12}],
      "outputs": [{"name": "STRING", "type": "STRING", "links": null}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "PreviewAny"},
      "widgets_values": [null, null, null]
    },
    {
      "id": 13,
      "type": "PreviewAny",
      "pos": [-308, -483],
      "size": [384, 313],
      "flags": {},
      "order": 12,
      "mode": 0,
      "inputs": [{"name": "source", "type": "*", "link": 13}],
      "outputs": [{"name": "STRING", "type": "STRING", "links": [14]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "PreviewAny"},
      "widgets_values": [null, null, null]
    },
    {
      "id": 14,
      "type": "PreviewAny",
      "pos": [-515, -8],
      "size": [492, 115],
      "flags": {},
      "order": 13,
      "mode": 0,
      "inputs": [{"name": "source", "type": "*", "link": 15}],
      "outputs": [{"name": "STRING", "type": "STRING", "links": null}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.1", "Node name for S&R": "PreviewAny"},
      "widgets_values": [null, null, null]
    },
    {
      "id": 15,
      "type": "PreviewAny",
      "pos": [-515, 170],
      "size": [474, 216],
      "flags": {},
      "order": 14,
      "mode": 0,
      "inputs": [{"name": "source", "type": "*", "link": 16}],
      "outputs": [{"name": "STRING", "type": "STRING", "links": null}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.1", "Node name for S&R": "PreviewAny"},
      "widgets_values": [null, null, null]
    },
    {
      "id": 16,
      "type": "CLIPTextEncode",
      "pos": [100, -200],
      "size": [420, 130],
      "flags": {},
      "order": 16,
      "mode": 0,
      "inputs": [
        {"name": "clip", "type": "CLIP", "link": 6},
        {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": 14}
      ],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [17]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "CLIPTextEncode"},
      "widgets_values": [""],
      "color": "#232",
      "bgcolor": "#353"
    },
    {
      "id": 17,
      "type": "CLIPTextEncode",
      "pos": [1561, 399],
      "size": [632, 156],
      "flags": {},
      "order": 15,
      "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 5}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [18]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "CLIPTextEncode"},
      "widgets_values": ["perfect face, beauty portrait, fashion photography, instagram aesthetic, flawless skin, glamour lighting, perfect anatomy, smiling pose, commercial photography, clean digital art, anime, hyper polished rendering, plastic skin, glossy ai art, symmetrical face, text, watermark\nworst quality, low effort, glossy ai art, generic fantasy art, oversaturated colors, plastic skin, clean digital rendering, perfect symmetry, hyper polished, overly sharp, photorealistic perfection, generic cinematic wallpaper, empty composition, bland lighting, sterile atmosphere, cheerful mood, cartoon look, anime, text, logo, watermark"],
      "color": "#322",
      "bgcolor": "#533"
    },
    {
      "id": 18,
      "type": "KSampler",
      "pos": [1721, 522],
      "size": [298, 474],
      "flags": {},
      "order": 17,
      "mode": 0,
      "inputs": [
        {"name": "model", "type": "MODEL", "link": 4},
        {"name": "positive", "type": "CONDITIONING", "link": 17},
        {"name": "negative", "type": "CONDITIONING", "link": 18},
        {"name": "latent_image", "type": "LATENT", "link": 7}
      ],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [19]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "KSampler"},
      "widgets_values": [780251152903304, "randomize", 8, 1, "euler", "beta", 1],
      "color": "#332922",
      "bgcolor": "#593930"
    },
    {
      "id": 19,
      "type": "VAEDecode",
      "pos": [2019, 580],
      "size": [225, 71],
      "flags": {},
      "order": 18,
      "mode": 0,
      "inputs": [
        {"name": "samples", "type": "LATENT", "link": 19},
        {"name": "vae", "type": "VAE", "link": 3}
      ],
      "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [20]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "VAEDecode"},
      "widgets_values": []
    },
    {
      "id": 20,
      "type": "SaveImage",
      "pos": [2185, 109],
      "size": [799, 969],
      "flags": {},
      "order": 19,
      "mode": 0,
      "inputs": [{"name": "images", "type": "IMAGE", "link": 20}],
      "outputs": [],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "SaveImage"},
      "widgets_values": ["ComfyUI"],
      "color": "#2a363b",
      "bgcolor": "#3f5159"
    }
  ],
  "links": [
    [1, 1, 0, 4, 0, "MODEL"],
    [2, 2, 0, 4, 1, "CLIP"],
    [3, 3, 0, 19, 1, "VAE"],
    [4, 4, 0, 18, 0, "MODEL"],
    [5, 4, 1, 17, 0, "CLIP"],
    [6, 4, 1, 16, 0, "CLIP"],
    [7, 5, 0, 18, 3, "LATENT"],
    [8, 6, 0, 7, 0, "AUDIO"],
    [9, 7, 0, 8, 0, "AUDIO"],
    [10, 7, 0, 11, 0, "AUDIO"],
    [11, 9, 0, 10, 0, "STRING"],
    [12, 11, 0, 12, 0, "STRING"],
    [13, 11, 1, 13, 0, "STRING"],
    [14, 13, 0, 16, 1, "STRING"],
    [15, 11, 2, 14, 0, "STRING"],
    [16, 11, 3, 15, 0, "STRING"],
    [17, 16, 0, 18, 1, "CONDITIONING"],
    [18, 17, 0, 18, 2, "CONDITIONING"],
    [19, 18, 0, 19, 0, "LATENT"],
    [20, 19, 0, 20, 0, "IMAGE"]
  ],
  "groups": [],
  "config": {},
  "extra": {
    "ds": {"scale": 0.6, "offset": [-400, 500]},
    "frontendVersion": "1.43.18"
  },
  "version": 0.4
}
```

- [ ] **Step 3.2: Add `AudioMoodAnalyzerTimeline` section to `README.md`**

In `README.md`, add after the `## Audio Mood Analyzer (Advanced)` section:

```markdown
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
```

- [ ] **Step 3.3: Verify JSON parses cleanly**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -c "import json; json.load(open('example_workflow/example_timeline.json')); print('JSON OK')"
```

Expected: `JSON OK`

- [ ] **Step 3.4: Run full test suite one last time**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/ -v 2>&1 | tail -10
```

Expected: all tests PASSED.

- [ ] **Step 3.5: Commit everything**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && git add example_workflow/example_timeline.json README.md && git commit -m "feat: add example_timeline.json workflow and README section for Timeline node"
```

---

## Self-review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| `AudioMoodAnalyzerTimeline` inherits from `AudioMoodAnalyzer` | Task 1.3 |
| `n_segments` input (INT, default 8, min 2, max 32) | Task 1.3 |
| `n_segments` inserted before generate_* booleans | Task 1.3 |
| 4 output names: prompt_sequence_json, merge_prompts, environment_prompts, subject_prompt | Task 1.3 |
| Subject analysis runs once (not per segment) | Task 2.3 |
| Mood analysis + env prompt + merge prompt per segment | Task 2.3 |
| Segment slicing: equal duration, last absorbs remainder | Task 2.3 |
| `start_s` / `end_s` computed from sample indices | Task 2.3 |
| Per-segment error handling: failed call → empty string, run continues | Task 2.3 |
| `generate_*` booleans honored | Task 2.3 |
| `subject_prompt` repeated on each segment object in JSON | Task 2.3 |
| Node registered as "Audio Mood Analyzer (Timeline)" | Task 1.4 |
| Sample workflow with OllamaModelSelector, 4 PreviewAny, image generation path | Task 3.1 |
| README section for Timeline node | Task 3.2 |

All requirements covered. No placeholders.
