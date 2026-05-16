import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from audio_mood_analyzer import AudioMoodAnalyzerTimeline


def test_timeline_node_exists():
    node = AudioMoodAnalyzerTimeline()
    assert node is not None


def test_input_types_has_n_segments():
    inputs = AudioMoodAnalyzerTimeline.INPUT_TYPES()
    assert "n_segments" in inputs["required"]


def test_n_segments_default_is_8():
    inputs = AudioMoodAnalyzerTimeline.INPUT_TYPES()
    _, meta = inputs["required"]["n_segments"]
    assert meta["default"] == 8


def test_n_segments_inserted_before_generate_booleans():
    inputs = AudioMoodAnalyzerTimeline.INPUT_TYPES()
    keys = list(inputs["required"].keys())
    assert keys.index("n_segments") < keys.index("generate_environment_prompt")


def test_return_types_count_is_4():
    assert len(AudioMoodAnalyzerTimeline.RETURN_TYPES) == 4


def test_return_names_are_correct():
    assert AudioMoodAnalyzerTimeline.RETURN_NAMES == (
        "prompt_sequence_json", "merge_prompts", "environment_prompts", "subject_prompt"
    )
