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
    result = node._build_mood_prompt(
        DUMMY_FEATURES, "context",
        mood_prompt_override="custom mood: {features}"
    )
    assert "custom mood:" in result
    assert str(DUMMY_FEATURES["tempo_bpm"]) in result


def test_mood_override_skipped_when_empty():
    node = AudioMoodAnalyzerAdvanced()
    result = node._build_mood_prompt(DUMMY_FEATURES, "context", mood_prompt_override="")
    assert "art director" in result  # built-in template


def test_invalid_override_falls_back_to_builtin():
    node = AudioMoodAnalyzerAdvanced()
    result = node._build_mood_prompt(
        DUMMY_FEATURES, "context",
        mood_prompt_override="bad template: {nonexistent_variable}"
    )
    assert "art director" in result  # fell back
