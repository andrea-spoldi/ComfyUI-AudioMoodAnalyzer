"""Shared utilities for all fear-of-the-art nodes."""
import json
import time
import requests

_LOG = "[AudioMoodAnalyzer]"

STYLE_PRESETS = {
    "painterly": (
        "Target aesthetic: oil painting, raw expressive brushwork, emotionally loaded colour, "
        "controlled distortion. Reference painters: Francis Bacon, Egon Schiele, Lucian Freud. "
        "Avoid photorealism, digital gloss, and smooth gradients."
    ),
    "cinematic": (
        "Target aesthetic: wide cinematic frame, dramatic directional lighting, atmospheric haze, "
        "filmic grain and restrained desaturation. Reference directors: Tarkovsky, Wong Kar-wai, "
        "Villeneuve. Avoid flat lighting, TV aesthetics, and oversaturated colour."
    ),
    "raw": (
        "Target aesthetic: immediate, visceral, lo-fi. Grainy, desaturated, imperfect, "
        "documentary-adjacent. No production value. Avoid polish, glamour, and beauty lighting."
    ),
    "abstract": (
        "Target aesthetic: non-representational, gestural abstraction, colour field, "
        "mark-making as pure emotion. Reference: Rothko, Kiefer, Twombly. "
        "Avoid literal depiction of subjects or recognisable scenes."
    ),
    "custom": "",
}


def _build_style_block(style_preset: str, style_notes: str) -> str:
    base = STYLE_PRESETS.get(style_preset, "")
    notes = style_notes.strip()
    if base and notes:
        return f"{base}\n{notes}"
    return notes if notes else base


def _fmt_json(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _parse_resolution(resolution_str: str) -> tuple:
    try:
        for sep in ("×", "x"):
            if sep in resolution_str:
                w, h = resolution_str.split(sep, 1)
                return int(w.strip()), int(h.strip())
    except (ValueError, AttributeError, TypeError):
        pass
    print(f"{_LOG} ⚠ could not parse resolution '{resolution_str}' — defaulting to 1024×1024")
    return 1024, 1024


_COMPOSITION_FALLBACK = {
    "aspect_ratio": {
        "orientation": "square",
        "ratio": "1:1",
        "recommended_resolution": "1024x1024",
    },
    "subject_placement": {"position": "center", "size_weight": 0.5},
    "environment": {"weight": 0.5, "negative_space": "medium"},
    "camera": {"distance": "medium", "framing_style": "balanced", "crop": "none"},
}


def _ollama_generate(ollama_url, model, prompt, temperature, num_predict=-1):
    response = requests.post(
        ollama_url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        },
        timeout=600,
    )
    response.raise_for_status()
    data = response.json()
    thinking = data.get("thinking", "")
    if thinking:
        print(f"{_LOG}   thinking: {len(thinking)} chars")
    result = data.get("response", "").strip()
    if not result:
        print(f"{_LOG} ⚠ empty response from Ollama — diagnostics:")
        print(f"{_LOG}   done_reason : {data.get('done_reason', 'n/a')}")
        print(f"{_LOG}   eval_count  : {data.get('eval_count', 'n/a')}  (response tokens generated)")
        print(f"{_LOG}   prompt_eval : {data.get('prompt_eval_count', 'n/a')}  (prompt tokens)")
        print(f"{_LOG}   thinking    : {len(thinking)} chars")
        print(f"{_LOG}   response key present: {'response' in data}")
        if data.get("done_reason") == "length":
            print(
                f"{_LOG}   → token budget exhausted (done_reason=length); "
                "analysis calls use num_predict=-1 (unlimited) — check Ollama version or model context limit"
            )
        elif not thinking and not result:
            print(f"{_LOG}   → no thinking and no response; raw keys: {list(data.keys())}")
    return result


def _timed_generate(label, ollama_url, model, prompt, temperature, num_predict=-1):
    tok_info = f"  (max_tokens={num_predict})" if num_predict != -1 else ""
    print(f"{_LOG} ▶ {label}{tok_info}")
    t = time.time()
    result = _ollama_generate(ollama_url, model, prompt, temperature, num_predict)
    print(f"{_LOG} ✓ {label}  ({time.time()-t:.1f}s, {len(result)} chars)")
    return result


def _extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    print(
        f"{_LOG} ⚠ JSON parse failed — response may be truncated "
        f"({len(text)} chars received). Try raising max_tokens_analysis."
    )
    return {"error": "Could not parse model output as JSON", "raw_output": text}
