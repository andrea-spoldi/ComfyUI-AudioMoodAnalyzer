# TASKS

```json
{
  "project": "fear-of-the-art-audio-analyzer",
  "updated": "2026-05-16",

  "current_session": {
    "id": "S-003",
    "goal": "Add OllamaModelSelector utility node (T-004)",
    "task_ref": "T-004",
    "started": "2026-05-16",
    "status": "in-progress",
    "blocker": null
  },

  "backlog": [
    {
      "id": "T-004",
      "title": "OllamaModelSelector utility node",
      "description": "New node that queries GET {ollama_url}/api/tags and returns available model names. Output: STRING list (newline-separated) and a recommended default. Lets users pick a model without knowing the exact tag format.",
      "size": "S",
      "priority": 1,
      "status": "in-progress",
      "tags": ["feature", "ollama", "ux"]
    },
    {
      "id": "T-005",
      "title": "AudioMoodAnalyzerTimeline — per-segment prompt sequence",
      "description": "New node that takes audio + n_segments (INT, 4-32, default 8) and all existing analysis params. Divides audio into n equal time slices, runs mood analysis on each, generates environment/subject/merge prompts per segment. Outputs: prompt_sequence_json (STRING, JSON array with segment index, start/end seconds, and all three prompts) and merge_prompts (STRING, newline-separated merge prompts for image batch nodes).",
      "size": "M",
      "priority": 2,
      "status": "pending",
      "tags": ["feature", "video", "timeline"]
    },
    {
      "id": "T-006",
      "title": "AnimateDiff prompt schedule formatter",
      "description": "New node (or additional output on AudioMoodAnalyzerTimeline) that takes the prompt_sequence_json output and formats it as an AnimateDiff per-frame schedule string: '\"0\": \"...\", \"8\": \"...\"'. Parameters: total_frames (INT), fps (INT, for timing alignment). Depends on T-005.",
      "size": "M",
      "priority": 3,
      "status": "pending",
      "tags": ["feature", "video", "animatediff"]
    }
  ],

  "decisions": [
    {
      "id": "D-001",
      "date": "2026-05-16",
      "decision": "song_description and song_genre are injected into _build_subject_analysis_prompt conditionally — omitted cleanly from the prompt string when blank",
      "rationale": "Avoids sending empty/noisy sections to the LLM when the user leaves fields blank.",
      "supersedes": null
    },
    {
      "id": "D-002",
      "date": "2026-05-16",
      "decision": "custom_context is scoped to analysis prompts only; generation prompts use style_preset + style_notes instead",
      "rationale": "Analysis needs objectivity. Generation needs aesthetic direction. One field for both created friction.",
      "supersedes": null
    },
    {
      "id": "D-003",
      "date": "2026-05-16",
      "decision": "AudioMoodAnalyzerAdvanced inherits from AudioMoodAnalyzer; does not duplicate prompt logic",
      "rationale": "DRY. The advanced node only adds override checking.",
      "supersedes": null
    },
    {
      "id": "D-004",
      "date": "2026-05-16",
      "decision": "Example workflow uses dual CLIPTextEncode + ConditioningAverage instead of Text Concatenate",
      "rationale": "Separate conditionings let the sampler attend to environment and subject independently. Strength slider gives compositional control without re-running Qwen.",
      "supersedes": null
    },
    {
      "id": "D-005",
      "date": "2026-05-16",
      "decision": "Video support split into three tasks: OllamaModelSelector (S), AudioMoodAnalyzerTimeline (M), AnimateDiff formatter (M)",
      "rationale": "L-sized feature decomposed so each task ships something useful independently. T-006 depends on T-005; T-004 is standalone.",
      "supersedes": null
    }
  ],

  "completed": [
    {
      "id": "T-001",
      "title": "Add song_description and song_genre input fields",
      "completed_date": "2026-05-16",
      "session_ref": "S-001",
      "notes": "Added to INPUT_TYPES, analyze() signature, subject guard, and _build_subject_analysis_prompt. Conditional injection when blank."
    },
    {
      "id": "T-002",
      "title": "Option B: style presets + prompt refinement",
      "completed_date": "2026-05-16",
      "session_ref": "S-002",
      "notes": "Fixed 4 structural prompt bugs. STYLE_PRESETS + _build_style_block with tests. style_preset dropdown + style_notes inputs. Analysis keeps custom_context; generation uses style_block."
    },
    {
      "id": "T-003",
      "title": "Option C: AudioMoodAnalyzerAdvanced — full template overrides",
      "completed_date": "2026-05-16",
      "session_ref": "S-002",
      "notes": "New node inheriting from AudioMoodAnalyzer. 5 optional override fields via format_map with fallback. Thread-safe lock. 11 tests passing."
    }
  ]
}
```

## Backlog

| ID | Title | Size | Priority | Status |
|----|-------|------|----------|--------|
| T-004 | OllamaModelSelector utility node | S | 1 | in-progress |
| T-005 | AudioMoodAnalyzerTimeline — per-segment prompt sequence | M | 2 | pending |
| T-006 | AnimateDiff prompt schedule formatter | M | 3 | pending |

## Completed

| ID | Title | Completed | Session |
|----|-------|-----------|---------|
| T-001 | Add song_description and song_genre input fields | 2026-05-16 | S-001 |
| T-002 | Option B: style presets + prompt refinement | 2026-05-16 | S-002 |
| T-003 | Option C: AudioMoodAnalyzerAdvanced — full template overrides | 2026-05-16 | S-002 |

## Current Session

**S-003** — Add OllamaModelSelector utility node (T-004)
