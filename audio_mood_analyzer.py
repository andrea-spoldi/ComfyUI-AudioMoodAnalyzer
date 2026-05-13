import json
import requests
import numpy as np
import librosa


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
                "temperature": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.5,
                    "step": 0.1
                }),
                "custom_context": ("STRING", {
                    "multiline": True,
                    "default": (
                        "Analyze the music as pure sound, not lyrics. "
                        "Translate sonic qualities into dark, painterly, emotional visual direction."
                    )
                }),
                "lyrics_or_text": ("STRING", {
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
        temperature,
        custom_context,
        lyrics_or_text,
        generate_environment_prompt,
        generate_subject_prompt,
        generate_merge_prompt,
    ):
        y, sr = self._audio_to_numpy(audio)
        features = self._extract_features(y, sr)

        mood_prompt = self._build_mood_prompt(features, custom_context)
        raw_mood = self._ollama_generate(
            ollama_url=ollama_url,
            model=model,
            prompt=mood_prompt,
            temperature=temperature,
        )

        mood_json = self._extract_json(raw_mood)
        subject_json = {}

        if lyrics_or_text.strip():
            raw_subject = self._ollama_generate(
                ollama_url=ollama_url,
                model=model,
                prompt=self._build_subject_analysis_prompt(
                    lyrics_or_text=lyrics_or_text,
                    custom_context=custom_context,
                ),
                temperature=temperature,
            )
            subject_json = self._extract_json(raw_subject)

        summary = self._build_summary(mood_json)

        environment_prompt = ""
        subject_prompt = ""
        merge_prompt = ""

        if generate_environment_prompt:
            environment_prompt = self._ollama_generate(
                ollama_url=ollama_url,
                model=model,
                prompt=self._build_environment_prompt_request(
                    mood_json=mood_json,
                    subject_json=subject_json,
                    custom_context=custom_context,
                ),
                temperature=temperature,
            )

        if generate_subject_prompt:
            subject_prompt = self._ollama_generate(
                ollama_url=ollama_url,
                model=model,
                prompt=self._build_subject_prompt_request(
                    subject_json=subject_json,
                    custom_context=custom_context,
                ),
                temperature=temperature,
            )

        if generate_merge_prompt:
            merge_prompt = self._ollama_generate(
                ollama_url=ollama_url,
                model=model,
                prompt=self._build_merge_prompt_request(
                    mood_json=mood_json,
                    environment_prompt=environment_prompt,
                    subject_prompt=subject_prompt,
                    custom_context=custom_context,
                ),
                temperature=temperature,
            )

        return (
            json.dumps(mood_json, indent=2, ensure_ascii=False),
            json.dumps(subject_json, indent=2, ensure_ascii=False),
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

        # Common ComfyUI AUDIO shapes:
        # [batch, channels, samples]
        # [channels, samples]
        # [samples]
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

        return {
            "duration_seconds": round(float(duration), 2),
            "tempo_bpm": round(float(np.asarray(tempo).item()), 2),
            "beat_count": int(len(beats)),
            "rms_energy_mean": round(float(np.mean(rms)), 5),
            "rms_energy_max": round(float(np.max(rms)), 5),
            "rms_energy_min": round(float(np.min(rms)), 5),
            "dynamic_range": round(float(np.max(rms) - np.min(rms)), 5),
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

    def _ollama_generate(self, ollama_url, model, prompt, temperature):
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            },
            timeout=240,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

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
{json.dumps(features, indent=2)}

Transform these audio features into a visual mood sheet for image generation.

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

Focus on atmosphere, intensity, movement, emotional pressure, vulnerability,
darkness, contrast, rhythm and painterly interpretation.

Do not mention lyrics.
Do not quote the song.
"""

    def _build_environment_prompt_request(self, mood_json, subject_json, custom_context):
        return f"""
    You are an art director creating an environment-only image-generation prompt.

    Use the sonic mood analysis as the main source:
    {json.dumps(mood_json, indent=2, ensure_ascii=False)}

    Use the lyrical subject analysis only as subtle atmospheric influence:
    {json.dumps(subject_json, indent=2, ensure_ascii=False)}

    Additional creative context:
    {custom_context}

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

    def _build_subject_prompt_request(self, subject_json, custom_context):
        return f"""
You are an art director creating a subject-only image-generation prompt.

Use the following subject analysis extracted from lyrics or poetic text:
{json.dumps(subject_json, indent=2, ensure_ascii=False)}

Additional creative context:
{custom_context}

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

If:
    the source text is written in first person
Then:
    translate it into third-person visual language.
    do not preserve the original point of view.
    convert "I" into "a solitary figure", "the subject", "a person", or a more specific visual archetype.

    Focus on what can be seen externally: posture, expression, gesture, tension, gaze, movement, symbolic attributes.

Output only the final image-generation prompt.
"""

    def _build_merge_prompt_request(
        self,
        mood_json,
        environment_prompt,
        subject_prompt,
        custom_context,
    ):
        return f"""
You are an art director merging an environment prompt and a subject prompt
into one coherent final image-generation prompt.

Sonic mood analysis:
{json.dumps(mood_json, indent=2, ensure_ascii=False)}

Environment prompt:
{environment_prompt}

Subject prompt:
{subject_prompt}

Additional creative context:
{custom_context}

Create one unified final image-generation prompt.

Keep it:
- coherent
- painterly
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

    def _build_subject_analysis_prompt(self, lyrics_or_text, custom_context):
        return f"""
        You are an art director analyzing lyrics or poetic text to extract the HUMAN SUBJECT.

        Do not summarize the lyrics.
        Do not quote the lyrics.

        Additional creative context:
        {custom_context}

        Lyrics or source text:
        {lyrics_or_text}

        Return only valid JSON with this structure:
        {{
        "point_of_view": "",
          "third_person_subject_description": "",
          "visible_translation_of_inner_state": [],
          "narrative_voice": "",
          "subject_role": "",
          "subject_psychology": [],
          "emotional_conflict": [],
          "posture": [],
          "expression": [],
          "eyes_and_face": [],
          "body_language": [],
          "symbolic_attributes": [],
          "implied_motion": [],
          "visual_distortions": [],
          "avoid": []
        }}

        Analyze the lyrics as emotional source material, then convert them into third-person visual subject design.

        Do not quote the lyrics.
        Do not summarize the song.
        Do not copy lines from the lyrics.
        Do not keep first-person phrasing.

        Extract only visual and psychological information useful to design a human subject for painterly image generation.

        When the text says "I", infer a visible human subject:
        - posture
        - expression
        - gaze
        - body tension
        - movement
        - vulnerability
        - symbolic attributes

        The final output must describe the subject from the outside, as something an image model can render.
        """

NODE_CLASS_MAPPINGS = {
    "AudioMoodAnalyzer": AudioMoodAnalyzer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioMoodAnalyzer": "Audio Mood Analyzer"
}
