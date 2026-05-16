# TASKS

```json
{
  "project": "fear-of-the-art-audio-analyzer",
  "updated": "2026-05-16",

  "current_session": {
    "id": "S-002",
    "goal": "Implement Option B: style presets + prompt refinement on AudioMoodAnalyzer",
    "task_ref": "T-002",
    "started": "2026-05-16",
    "status": "in-progress",
    "blocker": null
  },

  "backlog": [
    {
      "id": "T-002",
      "title": "Option B: style presets + prompt refinement",
      "description": "Fix 4 structural bugs in prompts. Add STYLE_PRESETS dict + _build_style_block() helper. Add style_preset dropdown and style_notes inputs. Inject style block into 3 generation prompts. Clarify custom_context as analysis-only (remove from generation prompts). See spec: docs/superpowers/specs/2026-05-16-style-presets-design.md",
      "size": "M",
      "priority": 1,
      "status": "in-progress",
      "tags": ["prompts", "feature", "refactor"]
    },
    {
      "id": "T-003",
      "title": "Option C: AudioMoodAnalyzerAdvanced node with full template overrides",
      "description": "New node inheriting from AudioMoodAnalyzer. Adds 5 optional prompt override fields (one per _build_* method) in an optional INPUT_TYPES group. Override logic: non-empty = render via str.format_map() with documented variables, fallback to super() on error. Register as 'Audio Mood Analyzer (Advanced)'. See spec: docs/superpowers/specs/2026-05-16-advanced-node-design.md",
      "size": "M",
      "priority": 2,
      "status": "pending",
      "tags": ["feature", "advanced-node"]
    }
  ],

  "decisions": [
    {
      "id": "D-001",
      "date": "2026-05-16",
      "decision": "song_description and song_genre are injected into _build_subject_analysis_prompt conditionally — omitted cleanly from the prompt string when blank",
      "rationale": "Avoids sending empty/noisy sections to the LLM when the user leaves fields blank. Keeps prompt tight.",
      "supersedes": null
    },
    {
      "id": "D-002",
      "date": "2026-05-16",
      "decision": "custom_context is scoped to analysis prompts only; generation prompts use style_preset + style_notes instead",
      "rationale": "Analysis needs objectivity (style notes would bias JSON output). Generation needs aesthetic direction. Mixing them via one field created friction in both directions.",
      "supersedes": null
    },
    {
      "id": "D-003",
      "date": "2026-05-16",
      "decision": "AudioMoodAnalyzerAdvanced inherits from AudioMoodAnalyzer; does not duplicate prompt logic",
      "rationale": "DRY. The advanced node only adds override checking. All infrastructure (audio extraction, Ollama calls, JSON parsing) is inherited.",
      "supersedes": null
    }
  ],

  "completed": [
    {
      "id": "T-001",
      "title": "Add song_description and song_genre input fields",
      "completed_date": "2026-05-16",
      "session_ref": "S-001",
      "notes": "Added to INPUT_TYPES, analyze() signature, subject guard condition, and _build_subject_analysis_prompt. Conditional injection: fields omitted from prompt when blank."
    }
  ]
}
```

## Backlog

| ID | Title | Size | Priority | Status |
|----|-------|------|----------|--------|
| T-002 | Option B: style presets + prompt refinement | M | 1 | in-progress |
| T-003 | Option C: AudioMoodAnalyzerAdvanced — full template overrides | M | 2 | pending |

## Completed

| ID | Title | Completed | Session |
|----|-------|-----------|---------|
| T-001 | Add song_description and song_genre input fields | 2026-05-16 | S-001 |

## Current Session

**S-002** — Implement Option B: style presets + prompt refinement on AudioMoodAnalyzer
