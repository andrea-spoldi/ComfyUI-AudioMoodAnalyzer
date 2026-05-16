# TASKS

```json
{
  "project": "fear-of-the-art-audio-analyzer",
  "updated": "2026-05-16",

  "current_session": {
    "id": "S-003",
    "goal": "Add OllamaModelSelector (T-004) and AudioMoodAnalyzerTimeline (T-005)",
    "task_ref": "T-005",
    "started": "2026-05-16",
    "status": "done",
    "blocker": null
  },

  "backlog": [
    {
      "id": "T-006",
      "title": "AnimateDiff prompt schedule formatter",
      "description": "New node (or additional output on AudioMoodAnalyzerTimeline) that takes the prompt_sequence_json output and formats it as an AnimateDiff per-frame schedule string: '\"0\": \"...\", \"8\": \"...\"'. Parameters: total_frames (INT), fps (INT, for timing alignment). Depends on T-005.",
      "size": "M",
      "priority": 1,
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
      "rationale": "Separate conditionings let the sampler attend to environment and subject independently.",
      "supersedes": null
    },
    {
      "id": "D-005",
      "date": "2026-05-16",
      "decision": "Video support split into three tasks: OllamaModelSelector (S), AudioMoodAnalyzerTimeline (M), AnimateDiff formatter (M)",
      "rationale": "L-sized feature decomposed so each task ships something useful independently.",
      "supersedes": null
    },
    {
      "id": "D-006",
      "date": "2026-05-16",
      "decision": "AudioMoodAnalyzerTimeline runs subject analysis once (shared across segments); mood + env + merge run per segment",
      "rationale": "Subject (lyrics-driven) doesn't change with audio segment. Environment (sonic-driven) does. Avoids redundant calls.",
      "supersedes": null
    }
  ],

  "completed": [
    {
      "id": "T-001",
      "title": "Add song_description and song_genre input fields",
      "completed_date": "2026-05-16",
      "session_ref": "S-001",
      "notes": "Conditional injection when blank."
    },
    {
      "id": "T-002",
      "title": "Option B: style presets + prompt refinement",
      "completed_date": "2026-05-16",
      "session_ref": "S-002",
      "notes": "STYLE_PRESETS + _build_style_block. style_preset dropdown + style_notes. Phase split for custom_context."
    },
    {
      "id": "T-003",
      "title": "Option C: AudioMoodAnalyzerAdvanced — full template overrides",
      "completed_date": "2026-05-16",
      "session_ref": "S-002",
      "notes": "5 optional override fields via format_map with fallback. Thread-safe lock. 11 tests."
    },
    {
      "id": "T-004",
      "title": "OllamaModelSelector utility node",
      "completed_date": "2026-05-16",
      "session_ref": "S-003",
      "notes": "Queries /api/tags. Returns models_list (newline-separated) and first_model. Graceful error handling. 5 tests."
    },
    {
      "id": "T-005",
      "title": "AudioMoodAnalyzerTimeline — per-segment prompt sequence",
      "completed_date": "2026-05-16",
      "session_ref": "S-003",
      "notes": "N equal segments. Subject once. Mood+env+merge per segment. 4 outputs: prompt_sequence_json, merge_prompts, environment_prompts, subject_prompt. 16 tests. example_timeline.json + README section."
    }
  ]
}
```

## Backlog

| ID | Title | Size | Priority | Status |
|----|-------|------|----------|--------|
| T-006 | AnimateDiff prompt schedule formatter | M | 1 | pending |

## Completed

| ID | Title | Completed | Session |
|----|-------|-----------|---------|
| T-001 | Add song_description and song_genre input fields | 2026-05-16 | S-001 |
| T-002 | Option B: style presets + prompt refinement | 2026-05-16 | S-002 |
| T-003 | Option C: AudioMoodAnalyzerAdvanced | 2026-05-16 | S-002 |
| T-004 | OllamaModelSelector utility node | 2026-05-16 | S-003 |
| T-005 | AudioMoodAnalyzerTimeline | 2026-05-16 | S-003 |

## Current Session

**S-003** — done
