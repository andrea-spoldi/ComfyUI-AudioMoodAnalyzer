import numpy as np
import librosa

from .shared import _LOG, _fmt_json

_CLAP_MODEL_CACHE: dict = {}


def _resolve_clap_device(device_str: str) -> str:
    if device_str != "auto":
        return device_str
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _get_clap_model(model_name: str, device_str: str):
    key = (model_name, device_str)
    if key not in _CLAP_MODEL_CACHE:
        print(f"{_LOG} Loading CLAP model {model_name} on {device_str}…")
        from transformers import ClapModel, ClapProcessor
        model = ClapModel.from_pretrained(model_name)
        model.to(device_str)
        model.eval()
        processor = ClapProcessor.from_pretrained(model_name)
        _CLAP_MODEL_CACHE[key] = (model, processor)
    return _CLAP_MODEL_CACHE[key]


class ClapAudioAnalyzer:
    CATEGORY = "audio/analysis"
    FUNCTION = "analyze"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("clap_json", "semantic_summary")

    _DEFAULT_ANCHORS = (
        "dark atmospheric tension\nmelancholic isolation\naggressive emotional pressure\n"
        "fragile human vulnerability\nnocturnal fear\nritualistic heaviness\n"
        "dreamlike surreal space\nclaustrophobic anxiety\nslow emotional collapse\n"
        "explosive catharsis\ncold empty space\ndistorted memory\n"
        "spiritual dread\nsubmerged sadness\nviolent inner pressure"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "clap_model": ("STRING", {"default": "laion/clap-htsat-unfused"}),
                "clap_device": (["auto", "cpu", "cuda", "mps"], {"default": "auto"}),
                "clap_text_anchors": ("STRING", {
                    "multiline": True,
                    "default": cls._DEFAULT_ANCHORS,
                }),
            }
        }

    def analyze(self, audio, clap_model, clap_device, clap_text_anchors):
        try:
            import torch
            waveform = audio["waveform"]
            sr = int(audio["sample_rate"])
            if hasattr(waveform, "detach"):
                waveform = waveform.detach().cpu().numpy()
            y = np.asarray(waveform, dtype=np.float32)
            if y.ndim == 3:
                y = y[0]
            if y.ndim == 2:
                y = np.mean(y, axis=0)

            device = _resolve_clap_device(clap_device)
            model, processor = _get_clap_model(clap_model, device)

            target_sr = processor.feature_extractor.sampling_rate
            if sr != target_sr:
                y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
                sr = target_sr

            audio_inputs = processor(audio=[y], sampling_rate=sr, return_tensors="pt")
            audio_inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in audio_inputs.items()}
            with torch.no_grad():
                audio_emb = model.get_audio_features(**audio_inputs)
            if not isinstance(audio_emb, torch.Tensor):
                audio_emb = audio_emb.pooler_output
            audio_emb = audio_emb / audio_emb.norm(dim=-1, keepdim=True)

            anchors = [a.strip() for a in clap_text_anchors.strip().splitlines() if a.strip()]
            text_inputs = processor(text=anchors, return_tensors="pt", padding=True)
            text_inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in text_inputs.items()}
            with torch.no_grad():
                text_emb = model.get_text_features(**text_inputs)
            if not isinstance(text_emb, torch.Tensor):
                text_emb = text_emb.pooler_output
            text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)

            scores = (audio_emb @ text_emb.T).squeeze(0).cpu().tolist()
            ranked = sorted(zip(anchors, scores), key=lambda x: -x[1])
            top3 = ranked[:3]

            result = {
                "enabled": True,
                "model": clap_model,
                "embedding_dim": int(audio_emb.shape[-1]),
                "audio_embedding_norm": round(float(audio_emb.norm().item()), 4),
                "top_text_matches": [{"text": t, "score": round(s, 4)} for t, s in top3],
                "semantic_inference": [t for t, _ in top3],
            }
            summary = "CLAP: " + ", ".join(result["semantic_inference"])
            return (_fmt_json(result), summary)

        except Exception as exc:
            print(f"{_LOG} CLAP error: {exc}")
            error_result = {"enabled": True, "error": str(exc), "fallback": "librosa_only"}
            return (_fmt_json(error_result), "")


NODE_CLASS_MAPPINGS = {
    "ClapAudioAnalyzer": ClapAudioAnalyzer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ClapAudioAnalyzer": "CLAP Audio Analyzer",
}
