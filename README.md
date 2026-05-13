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
| `temperature` | FLOAT | LLM temperature 0.0–1.5 (default: `0.7`) |
| `custom_context` | STRING | Creative direction injected into every prompt |
| `lyrics_or_text` | STRING | Optional lyrics or text for subject analysis |
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
