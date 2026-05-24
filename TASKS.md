# TASKS

```json
{
  "project": "fear-of-the-art-audio-analyzer",
  "updated": "2026-05-24",

  "current_session": {
    "id": "S-010",
    "goal": "Refactor: split audio_mood_analyzer.py into per-concern modules (T-011 through T-016)",
    "task_ref": "T-016",
    "started": "2026-05-22",
    "status": "completed",
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
    },
    {
      "id": "D-009",
      "date": "2026-05-20",
      "decision": "New nodes go in dedicated module files (e.g. mood_json_nodes.py); __init__.py merges mappings with {**_A, **_B}",
      "rationale": "audio_mood_analyzer.py is already large; per-file modules improve maintainability and reduce token cost per edit session.",
      "supersedes": null
    },
    {
      "id": "D-010",
      "date": "2026-05-20",
      "decision": "PromptEnricher uses `if value is None` guard, not `if not value`",
      "rationale": "`if not value` incorrectly skips valid falsy JSON values (0, False, '0'). Only None (missing key) should be skipped; `if not joined` handles empty strings and empty lists downstream.",
      "supersedes": null
    },
    {
      "id": "D-008",
      "date": "2026-05-16",
      "decision": "CLAP integration is Option A — completely standalone ClapAudioAnalyzer node, zero changes to existing nodes",
      "rationale": "Adding clap_json as an output to AudioMoodAnalyzer would shift output slot indices and break existing wired workflows.",
      "supersedes": null
    }
  ],

  "completed": [
    {
      "id": "S-006-fixes",
      "title": "ClapAudioAnalyzer runtime fixes",
      "completed_date": "2026-05-17",
      "session_ref": "S-006",
      "notes": "audios→audio kwarg; auto-resample to model's target_sr; unwrap BaseModelOutputWithPooling for both audio and text embeddings."
    },
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
    },
    {
      "id": "T-007",
      "title": "ClapAudioAnalyzer — standalone CLAP semantic embedding node",
      "completed_date": "2026-05-17",
      "session_ref": "S-005",
      "notes": "Option A standalone. _CLAP_MODEL_CACHE + _resolve_clap_device + _get_clap_model helpers. 19 tests. example_clap.json. transformers>=4.35.0 added to requirements."
    },
    {
      "id": "T-008",
      "title": "README refinement — philosophy, intent, experimental framing",
      "completed_date": "2026-05-17",
      "session_ref": "S-005",
      "notes": "Philosophy-first rewrite. CLAP + OllamaModelSelector documented. 4-section prose opening. Honest experimental framing. 267 lines."
    },
    {
      "id": "S-008-nodes",
      "title": "MoodJsonUnpacker + PromptEnricher — usability nodes",
      "completed_date": "2026-05-20",
      "session_ref": "S-008",
      "notes": "mood_json_nodes.py. MoodJsonUnpacker: 8 STRING outputs from mood_json. PromptEnricher: deterministic field injection. 14 tests. example_mood_unpack_enrich.json. README + CLAUDE.md updated."
    },
    {
      "id": "T-010",
      "title": "CompositionInferenceNode — core implementation",
      "completed_date": "2026-05-19",
      "session_ref": "S-007",
      "notes": "_parse_resolution, _COMPOSITION_FALLBACK, two-call pipeline, width/height INT outputs, composition_prompt STRING output."
    },
    {
      "id": "T-009",
      "title": "Tests for CompositionInferenceNode",
      "completed_date": "2026-05-22",
      "session_ref": "S-009",
      "notes": "30 tests. TestParseResolution (7), TestCompositionInferenceNodeMeta (7), TestCompositionInferenceNodeHappyPath (9), TestCompositionInferenceNodeFallback (7). All passing."
    },
    {
      "id": "S-010",
      "title": "Refactor: split audio_mood_analyzer.py into per-concern modules",
      "completed_date": "2026-05-24",
      "session_ref": "S-010",
      "notes": "T-011: shared.py (module-level utilities). T-012: formatter_nodes.py. T-013: clap_node.py. T-014: composition_node.py. T-015: analyzer_nodes.py. T-016: __init__.py updated, all 8 test files ported to per-module imports, audio_mood_analyzer.py deleted. 108 tests passing."
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

**S-007** — done. T-010 (CompositionInferenceNode core) complete. T-009 (tests) in backlog.
