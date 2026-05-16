import json
import threading
import time
import requests
import numpy as np
import librosa

_LOG = "[AudioMoodAnalyzer]"

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
        processor = ClapProcessor.from_pretrained(model_name)
        model.eval()
        _CLAP_MODEL_CACHE[key] = (model, processor)
    return _CLAP_MODEL_CACHE[key]

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


def _fmt_json(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


class AudioMoodAnalyzer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "ollama_url": ("STRING", {
                    "default": "http://localhost:11434/api/generate"
                }),
                "model": ("STRING", {
                    "default": "qwen3:14b"
                }),
                "analysis_temperature": ("FLOAT", {
                    "default": 0.4,
                    "min": 0.0,
                    "max": 1.5,
                    "step": 0.1
                }),
                "prompt_temperature": ("FLOAT", {
                    "default": 0.8,
                    "min": 0.0,
                    "max": 1.5,
                    "step": 0.1
                }),
                "custom_context": ("STRING", {
                    "multiline": True,
                    "default": (
                        "Analyze the music as pure sound, not lyrics. "
                        "Translate sonic qualities into emotional visual direction."
                    )
                }),
                "lyrics_or_text": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
                "focus_fragment": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
                "song_title": ("STRING", {
                    "default": ""
                }),
                "song_description": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
                "song_genre": ("STRING", {
                    "default": ""
                }),
                "style_preset": (
                    ["painterly", "cinematic", "raw", "abstract", "custom"],
                    {"default": "painterly"}
                ),
                "style_notes": ("STRING", {
                    "multiline": True,
                    "default": ""
                }),
                "generate_environment_prompt": ("BOOLEAN", {"default": True}),
                "generate_subject_prompt": ("BOOLEAN", {"default": True}),
                "generate_merge_prompt": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = (
        "mood_json",
        "subject_json",
        "environment_prompt",
        "subject_prompt",
        "merge_prompt",
        "summary"
    )

    FUNCTION = "analyze"
    CATEGORY = "audio/analysis"

    def analyze(
        self,
        audio,
        ollama_url,
        model,
        analysis_temperature,
        prompt_temperature,
        custom_context,
        lyrics_or_text,
        focus_fragment,
        song_title,
        song_description,
        song_genre,
        style_preset,
        style_notes,
        generate_environment_prompt,
        generate_subject_prompt,
        generate_merge_prompt,
    ):
        t0 = time.time()
        y, sr = self._audio_to_numpy(audio)
        features = self._extract_features(y, sr)
        duration = features.get("duration_seconds", "?")
        print(f"{_LOG} audio: {duration}s  model: {model}")

        style_block = _build_style_block(style_preset, style_notes)

        raw_mood = self._timed_generate(
            "mood analysis", ollama_url, model,
            self._build_mood_prompt(features, custom_context),
            analysis_temperature,
        )
        mood_json = self._extract_json(raw_mood)
        subject_json = {}

        if (lyrics_or_text.strip() or focus_fragment.strip() or song_title.strip()
                or song_description.strip() or song_genre.strip()):
            raw_subject = self._timed_generate(
                "subject analysis", ollama_url, model,
                self._build_subject_analysis_prompt(
                    lyrics_or_text=lyrics_or_text,
                    focus_fragment=focus_fragment,
                    custom_context=custom_context,
                    song_title=song_title,
                    song_description=song_description,
                    song_genre=song_genre,
                ),
                analysis_temperature,
            )
            subject_json = self._extract_json(raw_subject)

        summary = self._build_summary(mood_json)

        environment_prompt = ""
        subject_prompt = ""
        merge_prompt = ""

        if generate_environment_prompt:
            environment_prompt = self._timed_generate(
                "environment prompt", ollama_url, model,
                self._build_environment_prompt_request(
                    mood_json=mood_json,
                    subject_json=subject_json,
                    style_block=style_block,
                ),
                prompt_temperature,
            )

        if generate_subject_prompt:
            if subject_json and "error" not in subject_json:
                subject_prompt = self._timed_generate(
                    "subject prompt", ollama_url, model,
                    self._build_subject_prompt_request(
                        subject_json=subject_json,
                        style_block=style_block,
                    ),
                    prompt_temperature,
                )
            else:
                print(f"{_LOG} ⚠ subject prompt skipped — no subject analysis available (provide lyrics, focus_fragment, or song_title)")

        if generate_merge_prompt:
            merge_prompt = self._timed_generate(
                "merge prompt", ollama_url, model,
                self._build_merge_prompt_request(
                    mood_summary=summary,
                    environment_prompt=environment_prompt,
                    subject_prompt=subject_prompt,
                    style_block=style_block,
                ),
                prompt_temperature,
            )

        print(f"{_LOG} done  total: {time.time()-t0:.1f}s")

        return (
            _fmt_json(mood_json),
            _fmt_json(subject_json),
            environment_prompt,
            subject_prompt,
            merge_prompt,
            summary,
        )

    def _audio_to_numpy(self, audio):
        waveform = audio.get("waveform")
        sr = audio.get("sample_rate")

        if waveform is None or sr is None:
            raise ValueError("Invalid AUDIO input: missing waveform or sample_rate")

        y = waveform

        if hasattr(y, "detach"):
            y = y.detach().cpu().numpy()

        y = np.asarray(y)

        # ComfyUI AUDIO may arrive as [batch, channels, samples], [channels, samples], or [samples]
        if y.ndim == 3:
            y = y[0]

        if y.ndim == 2:
            y = np.mean(y, axis=0)

        if y.ndim != 1:
            raise ValueError(f"Unsupported audio waveform shape: {y.shape}")

        return y.astype(np.float32), int(sr)

    def _extract_features(self, y, sr):
        duration = librosa.get_duration(y=y, sr=sr)

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

        rms = librosa.feature.rms(y=y)[0]
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        zcr = librosa.feature.zero_crossing_rate(y=y)[0]
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)

        sections = self._section_energy(y, sections=8)

        rms_max = float(np.max(rms))
        rms_min = float(np.min(rms))

        return {
            "duration_seconds": round(float(duration), 2),
            "tempo_bpm": round(float(np.asarray(tempo).item()), 2),
            "beat_count": int(len(beats)),
            "rms_energy_mean": round(float(np.mean(rms)), 5),
            "rms_energy_max": round(rms_max, 5),
            "rms_energy_min": round(rms_min, 5),
            "dynamic_range": round(rms_max - rms_min, 5),
            "brightness_mean_spectral_centroid": round(float(np.mean(centroid)), 2),
            "brightness_max_spectral_centroid": round(float(np.max(centroid)), 2),
            "spectral_bandwidth_mean": round(float(np.mean(bandwidth)), 2),
            "zero_crossing_rate_mean": round(float(np.mean(zcr)), 5),
            "onset_strength_mean": round(float(np.mean(onset_env)), 5),
            "onset_strength_max": round(float(np.max(onset_env)), 5),
            "energy_sections": sections,
        }

    def _section_energy(self, y, sections=8):
        chunks = np.array_split(y, sections)
        result = []

        for idx, chunk in enumerate(chunks):
            rms = librosa.feature.rms(y=chunk)[0]
            result.append({
                "section": idx + 1,
                "energy_mean": round(float(np.mean(rms)), 5),
                "energy_peak": round(float(np.max(rms)), 5),
            })

        return result

    def _timed_generate(self, label, ollama_url, model, prompt, temperature, num_predict=-1):
        tok_info = f"  (max_tokens={num_predict})" if num_predict != -1 else ""
        print(f"{_LOG} ▶ {label}{tok_info}")
        t = time.time()
        result = self._ollama_generate(ollama_url, model, prompt, temperature, num_predict)
        print(f"{_LOG} ✓ {label}  ({time.time()-t:.1f}s, {len(result)} chars)")
        return result

    def _ollama_generate(self, ollama_url, model, prompt, temperature, num_predict=-1):
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": num_predict
                }
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
                print(f"{_LOG}   → token budget exhausted (done_reason=length); analysis calls use num_predict=-1 (unlimited) — check Ollama version or model context limit")
            elif not thinking and not result:
                print(f"{_LOG}   → no thinking and no response; raw keys: {list(data.keys())}")
        return result

    def _build_mood_prompt(self, features, custom_context):
        return f"""
You are an art director analyzing music as pure sound.

Do not use lyrics.
Do not infer meaning from words.
Analyze only the sonic features described below:
tempo, dynamics, energy, density, brightness, darkness, rhythm, tension,
loudness changes, and instrumental pressure.

Additional creative context:
{custom_context}

Audio features:
{_fmt_json(features)}

Transform these audio features into a visual mood sheet for image generation.

Focus on atmosphere, intensity, movement, emotional pressure, vulnerability,
darkness, contrast, rhythm and painterly interpretation.

Do not mention lyrics.
Do not quote the song.

Return only valid JSON with this structure:
{{
  "sonic_mood": [],
  "energy_profile": "",
  "tension_profile": "",
  "visual_environment_implications": [],
  "lighting_implications": [],
  "color_palette": [],
  "texture_implications": [],
  "subject_presence": [],
  "composition_suggestions": [],
  "motion_feel": [],
  "camera_language": [],
  "avoid": []
}}

Do not include any text before or after the JSON.
"""

    def _build_environment_prompt_request(self, mood_json, subject_json, style_block):
        style_section = f"\nVisual style target:\n{style_block}\n" if style_block.strip() else ""
        return f"""
You are an art director creating an environment-only image-generation prompt.
{style_section}
Use the sonic mood analysis as the main source:
{_fmt_json(mood_json)}

Use the lyrical subject analysis only as subtle atmospheric influence:
{_fmt_json(subject_json)}

Create a prompt for the ENVIRONMENT ONLY.
No people.
No human subjects.
No portraits.

Focus on:
- location
- atmosphere
- darkness
- lighting
- color palette
- spatial pressure
- painterly texture
- emotional landscape
- composition
- visual rhythm

Avoid:
- literal illustration of the lyrics
- generic masterpiece tags
- glossy AI look
- literal horror clichés

Output only the final image-generation prompt.
"""

    def _build_subject_prompt_request(self, subject_json, style_block):
        style_section = f"\nVisual style target:\n{style_block}\n" if style_block.strip() else ""
        return f"""
You are an art director creating a subject-only image-generation prompt.
{style_section}
Use the following subject analysis extracted from lyrics or poetic text:
{_fmt_json(subject_json)}

Create a prompt for the HUMAN SUBJECT ONLY.
Use a minimal or neutral background.

Focus on:
- posture
- expression
- emotional state
- body tension
- face and eyes
- vulnerability
- subtle distortion
- symbolic attributes
- painterly texture
- psychological pressure

Avoid:
- generic beauty portrait
- glossy AI look
- perfect anatomy obsession
- literal horror clichés
- overdescribing

If the source text is written in first person,
translate it into third-person visual language.
Do not preserve the original point of view.
Convert "I" into "a solitary figure", "the subject", "a person", or a more specific visual archetype.
Focus on what can be seen externally: posture, expression, gesture, tension, gaze, movement, symbolic attributes.

Output only the final image-generation prompt.
"""

    def _build_merge_prompt_request(
        self,
        mood_summary,
        environment_prompt,
        subject_prompt,
        style_block,
    ):
        style_section = f"\nVisual style target:\n{style_block}\n" if style_block.strip() else ""
        if subject_prompt.strip():
            subject_section = f"Subject prompt:\n{subject_prompt}\n"
            task_instruction = (
                "Merge the environment and subject into one coherent final image-generation prompt."
            )
        else:
            subject_section = ""
            task_instruction = (
                "Refine and elevate the environment prompt into a final image-generation prompt. "
                "No human subject is present — keep the focus on atmosphere, landscape, and mood."
            )

        return f"""
You are an art director composing a final image-generation prompt.
{style_section}
Sonic mood summary:
{mood_summary}

Environment prompt:
{environment_prompt}
{subject_section}
{task_instruction}

Keep it:
- coherent
- emotional
- atmospheric
- symbolic
- visually specific
- suitable for image generation

Avoid:
- generic masterpiece tags
- glossy AI look
- repetitive adjectives
- literal horror clichés
- excessive camera jargon
- overdescribing

Output only the final image-generation prompt.
"""

    def _extract_json(self, text):
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
            return {
                "error": "Could not parse model output as JSON",
                "raw_output": text
            }

    def _build_summary(self, mood_json):
        if "error" in mood_json:
            return mood_json.get("raw_output", "")

        mood = ", ".join(mood_json.get("sonic_mood", []))
        energy = mood_json.get("energy_profile", "")
        tension = mood_json.get("tension_profile", "")

        return f"Mood: {mood}\nEnergy: {energy}\nTension: {tension}"

    def _build_subject_analysis_prompt(
        self,
        lyrics_or_text,
        focus_fragment,
        song_title,
        custom_context,
        song_description="",
        song_genre="",
    ):
        title_line = f"\nSong title:\n{song_title}" if song_title.strip() else ""
        genre_line = f"\nGenre / style:\n{song_genre}" if song_genre.strip() else ""
        description_block = (
            f"\nSong description (general meaning, emotional arc, artist intent):\n{song_description}"
            if song_description.strip() else ""
        )
        return f"""
You are an art director analyzing lyrics or poetic text to extract the HUMAN SUBJECT.

Do not summarize the lyrics.
Do not quote the lyrics.
Do not copy lines from the lyrics.

Your goal is to infer a visually renderable human subject from emotional and symbolic material.

Additional creative context:
{custom_context}{title_line}{genre_line}{description_block}

Full lyrics or source text:
{lyrics_or_text}

Focus fragment:
{focus_fragment}

Use the song title, genre, and description as thematic and symbolic context.
The focus fragment is the PRIMARY emotional and visual anchor.
Use the rest of the lyrics only as secondary atmospheric context.

If the source text is written in first person,
translate it into third-person visual language.

Do not preserve the original point of view.

Convert internal emotions into visible external characteristics:
- posture
- expression
- gaze
- body tension
- movement
- symbolic attributes
- emotional pressure
- vulnerability
- psychological instability

Return only valid JSON with this structure:
{{
  "narrative_voice": "",
  "subject_role": "",
  "third_person_subject_description": "",
  "subject_psychology": [],
  "emotional_conflict": [],
  "posture": [],
  "expression": [],
  "eyes_and_face": [],
  "body_language": [],
  "symbolic_attributes": [],
  "implied_motion": [],
  "visible_translation_of_inner_state": [],
  "visual_distortions": [],
  "avoid": []
}}

Focus on emotional specificity rather than generic symbolism.

The final subject should feel visually concrete, emotionally vulnerable,
psychologically believable, and suitable for painterly image generation.

Do not include any text before or after the JSON.
"""

class AudioMoodAnalyzerAdvanced(AudioMoodAnalyzer):
    """AudioMoodAnalyzer with optional full prompt template overrides."""

    def __init__(self):
        self._analyze_lock = threading.Lock()

    @classmethod
    def INPUT_TYPES(cls):
        base = dict(super().INPUT_TYPES())
        base["optional"] = {
            "mood_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the audio mood analysis prompt. Leave empty to use built-in. "
                    "Available variables: {features}, {custom_context}, {style_block}"
                ),
            }),
            "subject_analysis_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the subject analysis prompt. Leave empty to use built-in. "
                    "Available variables: {lyrics_or_text}, {focus_fragment}, "
                    "{song_title}, {song_description}, {song_genre}, {custom_context}"
                ),
            }),
            "environment_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the environment image-gen prompt. Leave empty to use built-in. "
                    "Available variables: {mood_json}, {subject_json}, {style_block}"
                ),
            }),
            "subject_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the subject image-gen prompt. Leave empty to use built-in. "
                    "Available variables: {subject_json}, {style_block}"
                ),
            }),
            "merge_prompt_override": ("STRING", {
                "multiline": True,
                "default": "",
                "tooltip": (
                    "Override the merge prompt. Leave empty to use built-in. "
                    "Available variables: {mood_summary}, {environment_prompt}, "
                    "{subject_prompt}, {style_block}"
                ),
            }),
        }
        return base

    FUNCTION = "analyze"
    CATEGORY = "audio/analysis"

    def _render_override(self, template: str, context: dict, label: str) -> str | None:
        if not template.strip():
            return None
        try:
            return template.format_map(context)
        except (KeyError, ValueError) as exc:
            print(f"{_LOG} ⚠ {label} override render failed ({exc}); using built-in template")
            return None

    def analyze(
        self,
        audio,
        ollama_url,
        model,
        analysis_temperature,
        prompt_temperature,
        custom_context,
        lyrics_or_text,
        focus_fragment,
        song_title,
        song_description,
        song_genre,
        style_preset,
        style_notes,
        generate_environment_prompt,
        generate_subject_prompt,
        generate_merge_prompt,
        mood_prompt_override="",
        subject_analysis_prompt_override="",
        environment_prompt_override="",
        subject_prompt_override="",
        merge_prompt_override="",
    ):
        with self._analyze_lock:
            self._style_block = _build_style_block(style_preset, style_notes)
            self._mood_prompt_override = mood_prompt_override
            self._subject_analysis_prompt_override = subject_analysis_prompt_override
            self._environment_prompt_override = environment_prompt_override
            self._subject_prompt_override = subject_prompt_override
            self._merge_prompt_override = merge_prompt_override
            return super().analyze(
                audio=audio,
                ollama_url=ollama_url,
                model=model,
                analysis_temperature=analysis_temperature,
                prompt_temperature=prompt_temperature,
                custom_context=custom_context,
                lyrics_or_text=lyrics_or_text,
                focus_fragment=focus_fragment,
                song_title=song_title,
                song_description=song_description,
                song_genre=song_genre,
                style_preset=style_preset,
                style_notes=style_notes,
                generate_environment_prompt=generate_environment_prompt,
                generate_subject_prompt=generate_subject_prompt,
                generate_merge_prompt=generate_merge_prompt,
            )

    def _build_mood_prompt(self, features, custom_context):
        rendered = self._render_override(
            getattr(self, "_mood_prompt_override", ""),
            {
                "features": _fmt_json(features),
                "custom_context": custom_context,
                "style_block": getattr(self, "_style_block", ""),
            },
            "mood_prompt",
        )
        return rendered if rendered is not None else super()._build_mood_prompt(features, custom_context)

    def _build_subject_analysis_prompt(
        self,
        lyrics_or_text,
        focus_fragment,
        song_title,
        custom_context,
        song_description="",
        song_genre="",
    ):
        rendered = self._render_override(
            getattr(self, "_subject_analysis_prompt_override", ""),
            {
                "lyrics_or_text": lyrics_or_text,
                "focus_fragment": focus_fragment,
                "song_title": song_title,
                "song_description": song_description,
                "song_genre": song_genre,
                "custom_context": custom_context,
            },
            "subject_analysis_prompt",
        )
        return rendered if rendered is not None else super()._build_subject_analysis_prompt(
            lyrics_or_text=lyrics_or_text,
            focus_fragment=focus_fragment,
            song_title=song_title,
            custom_context=custom_context,
            song_description=song_description,
            song_genre=song_genre,
        )

    def _build_environment_prompt_request(self, mood_json, subject_json, style_block):
        rendered = self._render_override(
            getattr(self, "_environment_prompt_override", ""),
            {
                "mood_json": _fmt_json(mood_json),
                "subject_json": _fmt_json(subject_json),
                "style_block": style_block,
            },
            "environment_prompt",
        )
        return rendered if rendered is not None else super()._build_environment_prompt_request(
            mood_json=mood_json,
            subject_json=subject_json,
            style_block=style_block,
        )

    def _build_subject_prompt_request(self, subject_json, style_block):
        rendered = self._render_override(
            getattr(self, "_subject_prompt_override", ""),
            {
                "subject_json": _fmt_json(subject_json),
                "style_block": style_block,
            },
            "subject_prompt",
        )
        return rendered if rendered is not None else super()._build_subject_prompt_request(
            subject_json=subject_json,
            style_block=style_block,
        )

    def _build_merge_prompt_request(self, mood_summary, environment_prompt, subject_prompt, style_block):
        rendered = self._render_override(
            getattr(self, "_merge_prompt_override", ""),
            {
                "mood_summary": mood_summary,
                "environment_prompt": environment_prompt,
                "subject_prompt": subject_prompt,
                "style_block": style_block,
            },
            "merge_prompt",
        )
        return rendered if rendered is not None else super()._build_merge_prompt_request(
            mood_summary=mood_summary,
            environment_prompt=environment_prompt,
            subject_prompt=subject_prompt,
            style_block=style_block,
        )


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


class AudioMoodAnalyzerTimeline(AudioMoodAnalyzer):

    @classmethod
    def INPUT_TYPES(cls):
        parent = super().INPUT_TYPES()
        required = {}
        for k, v in parent["required"].items():
            if k == "generate_environment_prompt":
                required["n_segments"] = ("INT", {
                    "default": 8, "min": 2, "max": 32, "step": 1
                })
            required[k] = v
        parent["required"] = required
        return parent

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt_sequence_json", "merge_prompts", "environment_prompts", "subject_prompt")
    FUNCTION = "analyze_timeline"
    CATEGORY = "audio/analysis"

    def analyze_timeline(
        self,
        audio,
        ollama_url,
        model,
        analysis_temperature,
        prompt_temperature,
        custom_context,
        lyrics_or_text,
        focus_fragment,
        song_title,
        song_description,
        song_genre,
        style_preset,
        style_notes,
        n_segments,
        generate_environment_prompt,
        generate_subject_prompt,
        generate_merge_prompt,
    ):
        t0 = time.time()
        y, sr = self._audio_to_numpy(audio)
        style_block = _build_style_block(style_preset, style_notes)
        total_samples = len(y)
        seg_samples = total_samples // n_segments

        print(f"{_LOG} timeline: {n_segments} segments  "
              f"{round(total_samples / sr, 1)}s  model: {model}")

        # Subject analysis — once, shared across all segments
        subject_json = {}
        subject_prompt_str = ""
        has_subject_data = (
            lyrics_or_text.strip() or focus_fragment.strip() or song_title.strip()
            or song_description.strip() or song_genre.strip()
        )
        if has_subject_data:
            raw_subject = self._timed_generate(
                "subject analysis", ollama_url, model,
                self._build_subject_analysis_prompt(
                    lyrics_or_text=lyrics_or_text,
                    focus_fragment=focus_fragment,
                    song_title=song_title,
                    custom_context=custom_context,
                    song_description=song_description,
                    song_genre=song_genre,
                ),
                analysis_temperature,
            )
            subject_json = self._extract_json(raw_subject)
            if generate_subject_prompt and subject_json and "error" not in subject_json:
                subject_prompt_str = self._timed_generate(
                    "subject prompt", ollama_url, model,
                    self._build_subject_prompt_request(subject_json, style_block),
                    prompt_temperature,
                )

        segments = []
        for i in range(n_segments):
            start = i * seg_samples
            end = (i + 1) * seg_samples if i < n_segments - 1 else total_samples
            y_seg = y[start:end]
            start_s = round(start / sr, 2)
            end_s = round(end / sr, 2)

            features = self._extract_features(y_seg, sr)

            raw_mood = self._timed_generate(
                f"mood analysis [seg {i + 1}/{n_segments}]", ollama_url, model,
                self._build_mood_prompt(features, custom_context),
                analysis_temperature,
            )
            mood_json = self._extract_json(raw_mood)
            mood_summary = self._build_summary(mood_json)

            environment_prompt = ""
            if generate_environment_prompt:
                try:
                    environment_prompt = self._timed_generate(
                        f"environment prompt [seg {i + 1}/{n_segments}]", ollama_url, model,
                        self._build_environment_prompt_request(mood_json, subject_json, style_block),
                        prompt_temperature,
                    )
                except Exception as exc:
                    print(f"{_LOG} ⚠ environment prompt seg {i + 1} failed: {exc}")

            merge_prompt = ""
            if generate_merge_prompt:
                try:
                    merge_prompt = self._timed_generate(
                        f"merge prompt [seg {i + 1}/{n_segments}]", ollama_url, model,
                        self._build_merge_prompt_request(
                            mood_summary, environment_prompt, subject_prompt_str, style_block
                        ),
                        prompt_temperature,
                    )
                except Exception as exc:
                    print(f"{_LOG} ⚠ merge prompt seg {i + 1} failed: {exc}")

            segments.append({
                "segment": i + 1,
                "start_s": start_s,
                "end_s": end_s,
                "mood_json": mood_json,
                "environment_prompt": environment_prompt,
                "subject_prompt": subject_prompt_str,
                "merge_prompt": merge_prompt,
            })

        print(f"{_LOG} timeline done  total: {time.time() - t0:.1f}s")

        return (
            json.dumps(segments, indent=2, ensure_ascii=False),
            "\n".join(s["merge_prompt"] for s in segments),
            "\n".join(s["environment_prompt"] for s in segments),
            subject_prompt_str,
        )


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
    "AudioMoodAnalyzer": AudioMoodAnalyzer,
    "AudioMoodAnalyzerAdvanced": AudioMoodAnalyzerAdvanced,
    "AudioMoodAnalyzerTimeline": AudioMoodAnalyzerTimeline,
    "AnimateDiffScheduleFormatter": AnimateDiffScheduleFormatter,
    "OllamaModelSelector": OllamaModelSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioMoodAnalyzer": "Audio Mood Analyzer",
    "AudioMoodAnalyzerAdvanced": "Audio Mood Analyzer (Advanced)",
    "AudioMoodAnalyzerTimeline": "Audio Mood Analyzer (Timeline)",
    "AnimateDiffScheduleFormatter": "AnimateDiff Schedule Formatter",
    "OllamaModelSelector": "Ollama Model Selector",
}
