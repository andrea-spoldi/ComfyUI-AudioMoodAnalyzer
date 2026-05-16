# AnimateDiffScheduleFormatter — Implementation Plan (T-006)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `AnimateDiffScheduleFormatter`, a standalone ComfyUI node that converts `AudioMoodAnalyzerTimeline`'s `prompt_sequence_json` output into an AnimateDiff Evolved prompt travel schedule string with proportionally mapped frame numbers.

**Architecture:** Pure string-transform node — no Ollama calls, no audio processing, no inheritance. Parses the JSON, maps segment start times proportionally to `[0, total_frames)`, and formats each line as `"{frame}": "{prompt}",`. Placed in `audio_mood_analyzer.py` alongside the other nodes.

**Tech Stack:** Python 3.x, `json` (stdlib). No new dependencies.

**Prerequisite:** T-005 complete — `AudioMoodAnalyzerTimeline` must exist and produce `prompt_sequence_json`.

---

## File map

| File | Action |
|------|--------|
| `audio_mood_analyzer.py` | Modify — add `AnimateDiffScheduleFormatter` class and update registrations |
| `tests/test_animatediff_formatter.py` | Create — unit tests for format_schedule() |
| `example_workflow/example_animatediff.json` | Create — sample workflow |
| `README.md` | Modify — add AnimateDiff Formatter section |

---

### Task 1: Implement `AnimateDiffScheduleFormatter` with tests

**Files:**
- Modify: `audio_mood_analyzer.py`
- Create: `tests/test_animatediff_formatter.py`

- [ ] **Step 1.1: Create `tests/test_animatediff_formatter.py` with failing tests**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
from audio_mood_analyzer import AnimateDiffScheduleFormatter


def make_segments(n=4, total_duration=18.0, prompt_prefix="prompt"):
    seg_dur = total_duration / n
    segments = []
    for i in range(n):
        start = round(i * seg_dur, 2)
        end = round((i + 1) * seg_dur, 2) if i < n - 1 else total_duration
        segments.append({
            "segment": i + 1,
            "start_s": start,
            "end_s": end,
            "mood_json": {},
            "environment_prompt": f"env {prompt_prefix} {i + 1}",
            "subject_prompt": f"subj {prompt_prefix} {i + 1}",
            "merge_prompt": f"merge {prompt_prefix} {i + 1}",
        })
    return segments


DUMMY_SEQ_4 = json.dumps(make_segments(4, 18.0))


def test_returns_n_lines_for_n_segments():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    lines = [l for l in schedule.split("\n") if l.strip()]
    assert len(lines) == 4


def test_every_line_has_quoted_frame_colon_quoted_prompt_format():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    for line in schedule.split("\n"):
        if line.strip():
            assert line.startswith('"'), f"Line does not start with quote: {line!r}"
            assert '": "' in line, f"Line missing separator: {line!r}"
            assert line.endswith('",'), f"Line does not end with trailing comma: {line!r}"


def test_first_line_is_always_frame_0():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    first_line = [l for l in schedule.split("\n") if l.strip()][0]
    assert first_line.startswith('"0":')


def test_first_frame_prompt_matches_segment_1_prompt():
    node = AnimateDiffScheduleFormatter()
    _, first_frame_prompt = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    assert first_frame_prompt == "merge prompt 1"


def test_frames_are_proportionally_distributed():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    lines = [l for l in schedule.split("\n") if l.strip()]
    frames = [int(line.split('"')[1]) for line in lines]
    # 4 equal segments of 18s, total_frames=64:
    # seg1: 0/18*64=0, seg2: 4.5/18*64=16, seg3: 9/18*64=32, seg4: 13.5/18*64=48
    assert frames == [0, 16, 32, 48]


def test_empty_json_returns_empty_strings():
    node = AnimateDiffScheduleFormatter()
    schedule, first_frame_prompt = node.format_schedule("", 64, "merge_prompt")
    assert schedule == ""
    assert first_frame_prompt == ""


def test_invalid_json_returns_empty_strings():
    node = AnimateDiffScheduleFormatter()
    schedule, first_frame_prompt = node.format_schedule("not valid json", 64, "merge_prompt")
    assert schedule == ""
    assert first_frame_prompt == ""


def test_segments_with_empty_prompts_are_skipped():
    segments = make_segments(4, 18.0)
    segments[1]["merge_prompt"] = ""  # segment 2 has no merge prompt
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(json.dumps(segments), 64, "merge_prompt")
    lines = [l for l in schedule.split("\n") if l.strip()]
    assert len(lines) == 3  # segment 2 skipped


def test_prompt_type_environment_uses_environment_field():
    node = AnimateDiffScheduleFormatter()
    _, first_frame_prompt = node.format_schedule(DUMMY_SEQ_4, 64, "environment_prompt")
    assert first_frame_prompt == "env prompt 1"


def test_prompt_type_subject_uses_subject_field():
    node = AnimateDiffScheduleFormatter()
    _, first_frame_prompt = node.format_schedule(DUMMY_SEQ_4, 64, "subject_prompt")
    assert first_frame_prompt == "subj prompt 1"


def test_duplicate_frame_numbers_later_segment_wins():
    # total_frames=4 with 8 segments forces collisions
    segments = make_segments(8, 18.0)
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(json.dumps(segments), 4, "merge_prompt")
    # Must not crash; result is a valid non-empty schedule
    assert schedule != ""
    lines = [l for l in schedule.split("\n") if l.strip()]
    assert len(lines) <= 4  # at most 4 unique frames
```

- [ ] **Step 1.2: Run tests — confirm ImportError**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/test_animatediff_formatter.py -v 2>&1 | tail -5
```

Expected: `ImportError: cannot import name 'AnimateDiffScheduleFormatter'`

- [ ] **Step 1.3: Add `AnimateDiffScheduleFormatter` to `audio_mood_analyzer.py`**

Insert before `NODE_CLASS_MAPPINGS` (after `AudioMoodAnalyzerTimeline`):

```python
class AnimateDiffScheduleFormatter:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_sequence_json": ("STRING", {"default": ""}),
                "total_frames": ("INT", {"default": 64, "min": 8, "max": 256, "step": 1}),
                "prompt_type": (
                    ["merge_prompt", "environment_prompt", "subject_prompt"],
                    {"default": "merge_prompt"}
                ),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("schedule", "first_frame_prompt")
    FUNCTION = "format_schedule"
    CATEGORY = "audio/analysis"

    def format_schedule(self, prompt_sequence_json, total_frames, prompt_type):
        if not prompt_sequence_json.strip():
            return ("", "")

        try:
            segments = json.loads(prompt_sequence_json)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"{_LOG} ⚠ AnimateDiffScheduleFormatter: invalid JSON — {exc}")
            return ("", "")

        if not segments:
            print(f"{_LOG} ⚠ AnimateDiffScheduleFormatter: empty segments array")
            return ("", "")

        total_duration = segments[-1]["end_s"]
        if total_duration <= 0:
            print(f"{_LOG} ⚠ AnimateDiffScheduleFormatter: total_duration is zero")
            return ("", "")

        frame_map = {}
        for seg in segments:
            prompt = seg.get(prompt_type, "").strip()
            if not prompt:
                continue
            frame = round(seg["start_s"] / total_duration * total_frames)
            frame = max(0, min(frame, total_frames - 1))
            frame_map[frame] = prompt.replace('"', "'")

        if not frame_map:
            return ("", "")

        lines = [
            f'"{frame}": "{frame_map[frame]}",'
            for frame in sorted(frame_map.keys())
        ]
        schedule = "\n".join(lines)
        first_frame_prompt = frame_map.get(0, frame_map[min(frame_map.keys())])

        return (schedule, first_frame_prompt)
```

- [ ] **Step 1.4: Update `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`**

```python
NODE_CLASS_MAPPINGS = {
    "AudioMoodAnalyzer": AudioMoodAnalyzer,
    "AudioMoodAnalyzerAdvanced": AudioMoodAnalyzerAdvanced,
    "AudioMoodAnalyzerTimeline": AudioMoodAnalyzerTimeline,
    "AnimateDiffScheduleFormatter": AnimateDiffScheduleFormatter,
    "OllamaModelSelector": OllamaModelSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioMoodAnalyzer": "Audio Mood Analyzer",
    "AudioMoodAnalyzerAdvanced": "Audio Mood Analyzer (Advanced)",
    "AudioMoodAnalyzerTimeline": "Audio Mood Analyzer (Timeline)",
    "AnimateDiffScheduleFormatter": "AnimateDiff Schedule Formatter",
    "OllamaModelSelector": "Ollama Model Selector",
}
```

- [ ] **Step 1.5: Run all tests — expect all pass**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/ -v 2>&1 | tail -15
```

Expected: all tests PASSED (34 existing + 11 new = 45 total).

- [ ] **Step 1.6: Verify syntax**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -c "import ast; ast.parse(open('audio_mood_analyzer.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 1.7: Commit**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && git add audio_mood_analyzer.py tests/test_animatediff_formatter.py && git commit -m "feat: add AnimateDiffScheduleFormatter node with tests (T-006)"
```

---

### Task 2: Sample workflow + README section

**Files:**
- Create: `example_workflow/example_animatediff.json`
- Modify: `README.md`

- [ ] **Step 2.1: Create `example_workflow/example_animatediff.json`**

```json
{
  "id": "animatediff-example-001",
  "revision": 0,
  "last_node_id": 18,
  "last_link_id": 18,
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
      "order": 6,
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
      "pos": [-2400, 35],
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
      "type": "OllamaModelSelector",
      "pos": [-2400, 390],
      "size": [270, 58],
      "flags": {},
      "order": 5,
      "mode": 0,
      "inputs": [],
      "outputs": [
        {"name": "models_list", "type": "STRING", "links": [9]},
        {"name": "first_model", "type": "STRING", "links": null}
      ],
      "properties": {"cnr_id": "comfyui_fearnworksnodes", "Node name for S&R": "OllamaModelSelector"},
      "widgets_values": ["http://localhost:11434"]
    },
    {
      "id": 8,
      "type": "PreviewAny",
      "pos": [-2400, 530],
      "size": [380, 160],
      "flags": {},
      "order": 8,
      "mode": 0,
      "inputs": [{"name": "source", "type": "*", "link": 9}],
      "outputs": [{"name": "STRING", "type": "STRING", "links": null}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "PreviewAny"},
      "widgets_values": [null, null, null]
    },
    {
      "id": 9,
      "type": "AudioMoodAnalyzerTimeline",
      "pos": [-1800, 35],
      "size": [576, 870],
      "flags": {},
      "order": 7,
      "mode": 0,
      "inputs": [{"name": "audio", "type": "AUDIO", "link": 8}],
      "outputs": [
        {"name": "prompt_sequence_json", "type": "STRING", "links": [10, 11]},
        {"name": "merge_prompts", "type": "STRING", "links": null},
        {"name": "environment_prompts", "type": "STRING", "links": null},
        {"name": "subject_prompt", "type": "STRING", "links": null}
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
      "id": 10,
      "type": "PreviewAny",
      "pos": [-1150, -550],
      "size": [421, 420],
      "flags": {},
      "order": 9,
      "mode": 0,
      "inputs": [{"name": "source", "type": "*", "link": 10}],
      "outputs": [{"name": "STRING", "type": "STRING", "links": null}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "PreviewAny"},
      "widgets_values": [null, null, null]
    },
    {
      "id": 11,
      "type": "AnimateDiffScheduleFormatter",
      "pos": [-1150, 35],
      "size": [380, 130],
      "flags": {},
      "order": 10,
      "mode": 0,
      "inputs": [
        {"name": "prompt_sequence_json", "type": "STRING", "widget": {"name": "prompt_sequence_json"}, "link": 11}
      ],
      "outputs": [
        {"name": "schedule", "type": "STRING", "links": [12]},
        {"name": "first_frame_prompt", "type": "STRING", "links": [13]}
      ],
      "properties": {"cnr_id": "comfyui_fearnworksnodes", "Node name for S&R": "AnimateDiffScheduleFormatter"},
      "widgets_values": ["", 64, "merge_prompt"]
    },
    {
      "id": 12,
      "type": "PreviewAny",
      "pos": [-580, -200],
      "size": [460, 300],
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
      "pos": [-580, 150],
      "size": [460, 130],
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
      "type": "CLIPTextEncode",
      "pos": [80, -200],
      "size": [420, 130],
      "flags": {},
      "order": 14,
      "mode": 0,
      "inputs": [
        {"name": "clip", "type": "CLIP", "link": 5},
        {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": 14}
      ],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [15]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "CLIPTextEncode"},
      "widgets_values": [""],
      "color": "#232",
      "bgcolor": "#353"
    },
    {
      "id": 15,
      "type": "CLIPTextEncode",
      "pos": [1561, 399],
      "size": [632, 156],
      "flags": {},
      "order": 13,
      "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 6}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [16]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "CLIPTextEncode"},
      "widgets_values": ["perfect face, beauty portrait, fashion photography, instagram aesthetic, flawless skin, glamour lighting, perfect anatomy, smiling pose, commercial photography, clean digital art, anime, hyper polished rendering, plastic skin, glossy ai art, symmetrical face, text, watermark\nworst quality, low effort, glossy ai art, generic fantasy art, oversaturated colors, plastic skin, clean digital rendering, perfect symmetry, hyper polished, overly sharp, photorealistic perfection, generic cinematic wallpaper, empty composition, bland lighting, sterile atmosphere, cheerful mood, cartoon look, anime, text, logo, watermark"],
      "color": "#322",
      "bgcolor": "#533"
    },
    {
      "id": 16,
      "type": "KSampler",
      "pos": [1721, 522],
      "size": [298, 474],
      "flags": {},
      "order": 15,
      "mode": 0,
      "inputs": [
        {"name": "model", "type": "MODEL", "link": 4},
        {"name": "positive", "type": "CONDITIONING", "link": 15},
        {"name": "negative", "type": "CONDITIONING", "link": 16},
        {"name": "latent_image", "type": "LATENT", "link": 7}
      ],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [17]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "KSampler"},
      "widgets_values": [780251152903304, "randomize", 8, 1, "euler", "beta", 1],
      "color": "#332922",
      "bgcolor": "#593930"
    },
    {
      "id": 17,
      "type": "VAEDecode",
      "pos": [2019, 580],
      "size": [225, 71],
      "flags": {},
      "order": 16,
      "mode": 0,
      "inputs": [
        {"name": "samples", "type": "LATENT", "link": 17},
        {"name": "vae", "type": "VAE", "link": 3}
      ],
      "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [18]}],
      "properties": {"cnr_id": "comfy-core", "ver": "0.21.0", "Node name for S&R": "VAEDecode"},
      "widgets_values": []
    },
    {
      "id": 18,
      "type": "SaveImage",
      "pos": [2185, 109],
      "size": [799, 969],
      "flags": {},
      "order": 17,
      "mode": 0,
      "inputs": [{"name": "images", "type": "IMAGE", "link": 18}],
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
    [3, 3, 0, 17, 1, "VAE"],
    [4, 4, 0, 16, 0, "MODEL"],
    [5, 4, 1, 14, 0, "CLIP"],
    [6, 4, 1, 15, 0, "CLIP"],
    [7, 5, 0, 16, 3, "LATENT"],
    [8, 6, 0, 9, 0, "AUDIO"],
    [9, 7, 0, 8, 0, "STRING"],
    [10, 9, 0, 10, 0, "STRING"],
    [11, 9, 0, 11, 0, "STRING"],
    [12, 11, 0, 12, 0, "STRING"],
    [13, 11, 1, 13, 0, "STRING"],
    [14, 13, 0, 14, 1, "STRING"],
    [15, 14, 0, 16, 1, "CONDITIONING"],
    [16, 15, 0, 16, 2, "CONDITIONING"],
    [17, 16, 0, 17, 0, "LATENT"],
    [18, 17, 0, 18, 0, "IMAGE"]
  ],
  "groups": [],
  "config": {},
  "extra": {
    "ds": {"scale": 0.55, "offset": [-200, 450]},
    "frontendVersion": "1.43.18"
  },
  "version": 0.4
}
```

- [ ] **Step 2.2: Verify JSON parses cleanly**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -c "
import json
d = json.load(open('example_workflow/example_animatediff.json'))
nodes = {n['id']: n['type'] for n in d['nodes']}
print('nodes:', len(d['nodes']), '| links:', len(d['links']))
for lnk in d['links']:
    lid, fn, fs, tn, ts, t = lnk
    print(f'  [{lid}] {nodes[fn]}[{fs}] -> {nodes[tn]}[{ts}] ({t})')
"
```

Expected: 18 nodes, 18 links. All node IDs resolve without KeyError.

- [ ] **Step 2.3: Add `AnimateDiff Schedule Formatter` section to `README.md`**

Append after the `## Audio Mood Analyzer (Timeline)` section and before `## License`:

```markdown
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
```

- [ ] **Step 2.4: Run full test suite**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && python3 -m pytest tests/ -v 2>&1 | tail -8
```

Expected: all 45 tests PASSED.

- [ ] **Step 2.5: Commit**

```bash
cd /Users/andreaspoldi/ComfyUI/custom_nodes/fear_of_the_art_audio_analyzer && git add example_workflow/example_animatediff.json README.md && git commit -m "feat: add example_animatediff.json workflow and README section for AnimateDiff formatter"
```

---

## Self-review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Standalone node (no inheritance) | Task 1.3 |
| `prompt_sequence_json` STRING input | Task 1.3 |
| `total_frames` INT input (default 64, min 8, max 256) | Task 1.3 |
| `prompt_type` COMBO input (3 options, default merge_prompt) | Task 1.3 |
| Frame = round(start_s / total_duration * total_frames), clamped | Task 1.3 |
| `schedule` output: `"{frame}": "{prompt}",` one line per segment | Task 1.3 |
| `first_frame_prompt` output: prompt for frame 0 | Task 1.3 |
| Empty prompt_sequence_json → ("", "") | Task 1.3 |
| Invalid JSON → ("", "") with log warning | Task 1.3 |
| Empty prompt field for segment → skip that keyframe | Task 1.3 |
| Duplicate frame numbers → later segment wins | Task 1.3 |
| Registered as "AnimateDiff Schedule Formatter" | Task 1.4 |
| Sample workflow with Timeline → Formatter → PreviewAny nodes | Task 2.1 |
| `schedule` wired to PreviewAny for inspection | Task 2.1 |
| `first_frame_prompt` wired through PreviewAny → CLIPTextEncode positive | Task 2.1 |
| OllamaModelSelector included | Task 2.1 |
| README section with inputs, outputs, format example | Task 2.3 |

All requirements covered. No placeholders.
