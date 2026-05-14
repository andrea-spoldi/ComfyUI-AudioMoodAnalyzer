# ComfyUI Audio Mood Analyzer

A ComfyUI custom node that extracts sonic features from audio and uses a local Ollama LLM to generate painterly, emotionally-driven image-generation prompts.

## Requirements

- [Ollama](https://ollama.com/) running locally with a model loaded (default: `qwen3:14b`)
- Python packages: `librosa`, `soundfile`, `numpy`, `requests`

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/andrea-spoldi/ComfyUI-AudioMoodAnalyzer.git
pip install -r ComfyUI-AudioMoodAnalyzer/requirements.txt
```

Restart ComfyUI. The node appears under **audio/analysis**.

## Inputs

| Name | Type | Description |
|------|------|-------------|
| `audio` | AUDIO | Audio input from any ComfyUI audio loader |
| `ollama_url` | STRING | Ollama API endpoint (default: `http://localhost:11434/api/generate`) |
| `model` | STRING | Ollama model name (default: `qwen3:14b`) |
| `analysis_temperature` | FLOAT | Temperature for structured JSON analysis calls — lower = more consistent (default: `0.4`) |
| `prompt_temperature` | FLOAT | Temperature for creative image-prompt generation calls — higher = more expressive (default: `0.8`) |
| `custom_context` | STRING | Creative direction injected into every prompt |
| `lyrics_or_text` | STRING | Optional full lyrics or source text for subject analysis |
| `focus_fragment` | STRING | Optional key line or phrase used as the primary emotional/visual anchor |
| `song_title` | STRING | Optional song title used as thematic and symbolic context |
| `generate_environment_prompt` | BOOLEAN | Generate an environment-only image prompt |
| `generate_subject_prompt` | BOOLEAN | Generate a subject-only image prompt |
| `generate_merge_prompt` | BOOLEAN | Generate a merged final image prompt |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| `mood_json` | STRING | Full sonic mood analysis as JSON |
| `subject_json` | STRING | Subject analysis from lyrics/text as JSON |
| `environment_prompt` | STRING | Image prompt focused on environment/atmosphere |
| `subject_prompt` | STRING | Image prompt focused on the human subject |
| `merge_prompt` | STRING | Unified final image-generation prompt |
| `summary` | STRING | Short human-readable mood summary |

## License

MIT — see [LICENSE](LICENSE).
