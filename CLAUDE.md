# fear-of-the-art-audio-analyzer

## Architecture constraints
- Single-file node: all logic lives in `audio_mood_analyzer.py`. No new files unless adding a separate utility module that warrants it.
- ComfyUI node inputs must be declared in `INPUT_TYPES` and mirrored as parameters in `analyze()`. Missing params break node loading.
- Ollama calls use `num_predict=-1` — never set a token limit; thinking models (qwen3 et al.) need unbounded output.
- Subject analysis is opt-in: only runs when at least one of lyrics_or_text, focus_fragment, song_title, song_description, or song_genre is non-empty.

## Intentional decisions
- `analysis_temperature` (0.4) and `prompt_temperature` (0.8) are separate: structured JSON calls use low temp, creative prompt generation uses high temp.
- Subject prompt is silently skipped (with a log warning) when no subject analysis is available — not an error.

## Stack
- Python 3.x, librosa, numpy, requests (no async)
- Ollama REST API at `/api/generate` (streaming=false)
- ComfyUI custom node conventions
