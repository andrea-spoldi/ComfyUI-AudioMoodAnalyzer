import json
import requests

from .shared import _LOG


class OllamaModelSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ollama_url": ("STRING", {"default": "http://localhost:11434"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("models_list", "first_model")
    FUNCTION = "list_models"
    CATEGORY = "audio/analysis"

    def list_models(self, ollama_url):
        try:
            base = ollama_url.rstrip("/")
            response = requests.get(f"{base}/api/tags", timeout=10)
            response.raise_for_status()
            models = [m["name"] for m in response.json().get("models", [])]
            if not models:
                return ("(no models found)", "")
            return ("\n".join(models), models[0])
        except Exception as exc:
            msg = f"(error querying Ollama: {exc})"
            print(f"{_LOG} ⚠ OllamaModelSelector: {exc}")
            return (msg, "")


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
            frame_map[frame] = prompt.replace('"', "'").replace("\n", " ").replace("\r", "")

        if not frame_map:
            return ("", "")

        lines = [
            f'"{frame}": "{frame_map[frame]}",'
            for frame in sorted(frame_map.keys())
        ]
        schedule = "\n".join(lines)
        first_frame_prompt = frame_map.get(0, frame_map[min(frame_map.keys())])

        return (schedule, first_frame_prompt)


NODE_CLASS_MAPPINGS = {
    "OllamaModelSelector": OllamaModelSelector,
    "AnimateDiffScheduleFormatter": AnimateDiffScheduleFormatter,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OllamaModelSelector": "Ollama Model Selector",
    "AnimateDiffScheduleFormatter": "AnimateDiff Schedule Formatter",
}
