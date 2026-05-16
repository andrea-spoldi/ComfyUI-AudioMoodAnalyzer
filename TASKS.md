# TASKS

```json
{
  "project": "fear-of-the-art-audio-analyzer",
  "updated": "2026-05-16",

  "current_session": {
    "id": "S-004",
    "goal": "Add AnimateDiffScheduleFormatter (T-006)",
    "task_ref": "T-006",
    "started": "2026-05-16",
    "status": "done",
    "blocker": null
  },

  "backlog": [],

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
      "rationale": "Analysis needs objectivity. Generation needs aesthetic direction.",
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
      "rationale": "Subject (lyrics-driven) doesn't change with audio segment. Environment (sonic-driven) does.",
      "supersedes": null
    },
    {
      "id": "D-007",
      "date": "2026-05-16",
      "decision": "AnimateDiffScheduleFormatter uses proportional frame mapping (start_s / total_duration × total_frames), not fps-based",
      "rationale": "Proportional mapping works regardless of song length or fps setting. fps is an AnimateDiff-side parameter.",
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
      "notes": "5 optional override fields via format_map with fallback. Thread-safe lock."
    },
    {
      "id": "T-004",
      "title": "OllamaModelSelector utility node",
      "completed_date": "2026-05-16",
      "session_ref": "S-003",
      "notes": "Queries /api/tags. Returns models_list and first_model. 5 tests."
    },
    {
      "id": "T-005",
      "title": "AudioMoodAnalyzerTimeline — per-segment prompt sequence",
      "completed_date": "2026-05-16",
      "session_ref": "S-003",
      "notes": "N equal segments. Subject once. Mood+env+merge per segment. 4 outputs. 16 tests. example_timeline.json + README."
    },
    {
      "id": "T-006",
      "title": "AnimateDiffScheduleFormatter — ADE prompt travel schedule",
      "completed_date": "2026-05-16",
      "session_ref": "S-004",
      "notes": "Proportional frame mapping. Newline sanitisation in prompts. 11 tests. example_animatediff.json + README."
    }
  ]
}
```

## Completed

| ID | Title | Completed | Session |
|----|-------|-----------|---------|
| T-001 | Add song_description and song_genre input fields | 2026-05-16 | S-001 |
| T-002 | Option B: style presets + prompt refinement | 2026-05-16 | S-002 |
| T-003 | Option C: AudioMoodAnalyzerAdvanced | 2026-05-16 | S-002 |
| T-004 | OllamaModelSelector utility node | 2026-05-16 | S-003 |
| T-005 | AudioMoodAnalyzerTimeline | 2026-05-16 | S-003 |
| T-006 | AnimateDiffScheduleFormatter | 2026-05-16 | S-004 |

## Current Session

**S-004** — done. Backlog empty.
