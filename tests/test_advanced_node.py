import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from audio_mood_analyzer import AudioMoodAnalyzerAdvanced, _fmt_json

DUMMY_FEATURES = {"duration_seconds": 30, "tempo_bpm": 120}
DUMMY_MOOD = {"sonic_mood": ["dark"], "energy_profile": "high", "tension_profile": "rising"}
DUMMY_SUBJECT = {"subject_role": "wanderer"}


def test_advanced_node_exists():
    node = AudioMoodAnalyzerAdvanced()
    assert node is not None


def test_input_types_has_override_fields():
    inputs = AudioMoodAnalyzerAdvanced.INPUT_TYPES()
    optional = inputs.get("optional", {})
    assert "mood_prompt_override" in optional
    assert "subject_analysis_prompt_override" in optional
    assert "environment_prompt_override" in optional
    assert "subject_prompt_override" in optional
    assert "merge_prompt_override" in optional


def test_mood_override_used_when_provided():
    node = AudioMoodAnalyzerAdvanced()
    node._mood_prompt_override = "custom mood: {features}"
    result = node._build_mood_prompt(DUMMY_FEATURES, "context")
    assert "custom mood:" in result
    assert str(DUMMY_FEATURES["tempo_bpm"]) in result


def test_mood_override_skipped_when_empty():
    node = AudioMoodAnalyzerAdvanced()
    node._mood_prompt_override = ""
    result = node._build_mood_prompt(DUMMY_FEATURES, "context")
    assert "art director" in result  # built-in template


def test_invalid_override_falls_back_to_builtin():
    node = AudioMoodAnalyzerAdvanced()
    node._mood_prompt_override = "bad template: {nonexistent_variable}"
    result = node._build_mood_prompt(DUMMY_FEATURES, "context")
    assert "art director" in result  # fell back


from unittest.mock import patch

def test_analyze_passes_override_to_mood_builder():
    """Verify that mood_prompt_override is rendered and passed to _timed_generate."""
    node = AudioMoodAnalyzerAdvanced()
    captured_prompts = []

    def fake_timed_generate(label, ollama_url, model, prompt, temperature, num_predict=-1):
        captured_prompts.append((label, prompt))
        if label == "mood analysis":
            return '{"sonic_mood":[],"energy_profile":"","tension_profile":"","visual_environment_implications":[],"lighting_implications":[],"color_palette":[],"texture_implications":[],"subject_presence":[],"composition_suggestions":[],"motion_feel":[],"camera_language":[],"avoid":[]}'
        return ""

    with patch.object(node, '_timed_generate', side_effect=fake_timed_generate), \
         patch.object(node, '_audio_to_numpy', return_value=([], 44100)), \
         patch.object(node, '_extract_features', return_value=DUMMY_FEATURES):
        node.analyze(
            audio={},
            ollama_url="http://localhost:11434/api/generate",
            model="test",
            analysis_temperature=0.4,
            prompt_temperature=0.8,
            custom_context="ctx",
            lyrics_or_text="",
            focus_fragment="",
            song_title="",
            song_description="",
            song_genre="",
            style_preset="painterly",
            style_notes="",
            generate_environment_prompt=False,
            generate_subject_prompt=False,
            generate_merge_prompt=False,
            mood_prompt_override="custom mood prompt: {features}",
            subject_analysis_prompt_override="",
            environment_prompt_override="",
            subject_prompt_override="",
            merge_prompt_override="",
        )

    mood_calls = [prompt for label, prompt in captured_prompts if label == "mood analysis"]
    assert len(mood_calls) == 1, "Expected exactly one mood analysis call"
    assert "custom mood prompt:" in mood_calls[0], (
        f"Override was not rendered into the prompt. Got: {mood_calls[0][:100]}"
    )
