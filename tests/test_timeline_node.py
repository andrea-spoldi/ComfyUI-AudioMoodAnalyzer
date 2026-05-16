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


import json
import numpy as np
from unittest.mock import patch

MOCK_MOOD_JSON_STR = json.dumps({
    "sonic_mood": ["dark"], "energy_profile": "high", "tension_profile": "rising",
    "visual_environment_implications": [], "lighting_implications": [],
    "color_palette": [], "texture_implications": [], "subject_presence": [],
    "composition_suggestions": [], "motion_feel": [], "camera_language": [], "avoid": []
})

MOCK_SUBJECT_JSON_STR = json.dumps({
    "narrative_voice": "first", "subject_role": "student",
    "third_person_subject_description": "a solitary figure",
    "subject_psychology": [], "emotional_conflict": [], "posture": [],
    "expression": [], "eyes_and_face": [], "body_language": [],
    "symbolic_attributes": [], "implied_motion": [],
    "visible_translation_of_inner_state": [], "visual_distortions": [], "avoid": []
})

DUMMY_FEATURES = {
    "duration_seconds": 4.5, "tempo_bpm": 120.0, "beat_count": 10,
    "rms_energy_mean": 0.0, "rms_energy_max": 0.0, "rms_energy_min": 0.0,
    "dynamic_range": 0.0, "brightness_mean_spectral_centroid": 0.0,
    "brightness_max_spectral_centroid": 0.0, "spectral_bandwidth_mean": 0.0,
    "zero_crossing_rate_mean": 0.0, "onset_strength_mean": 0.0,
    "onset_strength_max": 0.0, "energy_sections": []
}

DUMMY_Y = np.zeros(44100 * 18, dtype=np.float32)  # 18 seconds

CALL_COUNTER = {}


def fake_timed_generate(label, ollama_url, model, prompt, temperature, num_predict=-1):
    CALL_COUNTER[label] = CALL_COUNTER.get(label, 0) + 1
    if "mood analysis" in label:
        return MOCK_MOOD_JSON_STR
    if "subject analysis" in label:
        return MOCK_SUBJECT_JSON_STR
    if "subject prompt" in label:
        return "a solitary figure in shadows"
    if "environment prompt" in label:
        return "dark crumbling wasteland"
    if "merge prompt" in label:
        return f"unified prompt {CALL_COUNTER[label]}"
    return ""


def run_timeline(n_segments=4, lyrics="some lyrics", generate_subject_prompt=True):
    CALL_COUNTER.clear()
    node = AudioMoodAnalyzerTimeline()
    with patch.object(node, "_timed_generate", side_effect=fake_timed_generate), \
         patch.object(node, "_audio_to_numpy", return_value=(DUMMY_Y, 44100)), \
         patch.object(node, "_extract_features", return_value=DUMMY_FEATURES):
        return node.analyze_timeline(
            audio={},
            ollama_url="http://localhost:11434/api/generate",
            model="test",
            analysis_temperature=0.4,
            prompt_temperature=0.8,
            custom_context="ctx",
            lyrics_or_text=lyrics,
            focus_fragment="",
            song_title="",
            song_description="",
            song_genre="",
            style_preset="painterly",
            style_notes="",
            n_segments=n_segments,
            generate_environment_prompt=True,
            generate_subject_prompt=generate_subject_prompt,
            generate_merge_prompt=True,
        )


def test_analyze_timeline_returns_4_outputs():
    result = run_timeline(n_segments=4)
    assert len(result) == 4


def test_prompt_sequence_json_has_correct_segment_count():
    seq_json, _, _, _ = run_timeline(n_segments=4)
    segments = json.loads(seq_json)
    assert len(segments) == 4


def test_segment_schema_has_required_fields():
    seq_json, _, _, _ = run_timeline(n_segments=2)
    segments = json.loads(seq_json)
    for seg in segments:
        assert "segment" in seg
        assert "start_s" in seg
        assert "end_s" in seg
        assert "mood_json" in seg
        assert "environment_prompt" in seg
        assert "subject_prompt" in seg
        assert "merge_prompt" in seg


def test_segment_numbers_are_1_indexed():
    seq_json, _, _, _ = run_timeline(n_segments=3)
    segments = json.loads(seq_json)
    assert [s["segment"] for s in segments] == [1, 2, 3]


def test_segment_times_are_monotonic():
    seq_json, _, _, _ = run_timeline(n_segments=4)
    segments = json.loads(seq_json)
    for seg in segments:
        assert seg["start_s"] < seg["end_s"]
    for i in range(len(segments) - 1):
        assert segments[i]["end_s"] <= segments[i + 1]["start_s"]


def test_merge_prompts_has_n_lines():
    _, merge_prompts, _, _ = run_timeline(n_segments=4)
    lines = [l for l in merge_prompts.split("\n") if l.strip()]
    assert len(lines) == 4


def test_environment_prompts_has_n_lines():
    _, _, env_prompts, _ = run_timeline(n_segments=4)
    lines = [l for l in env_prompts.split("\n") if l.strip()]
    assert len(lines) == 4


def test_subject_prompt_is_single_string():
    _, _, _, subject_prompt = run_timeline(n_segments=4)
    assert isinstance(subject_prompt, str)
    assert "\n" not in subject_prompt or subject_prompt == ""


def test_no_lyrics_gives_empty_subject_prompt():
    _, _, _, subject_prompt = run_timeline(n_segments=2, lyrics="")
    assert subject_prompt == ""


def test_subject_prompt_repeated_in_each_segment():
    seq_json, _, _, subject_prompt = run_timeline(n_segments=3, lyrics="some lyrics")
    if subject_prompt:
        segments = json.loads(seq_json)
        for seg in segments:
            assert seg["subject_prompt"] == subject_prompt


def test_last_segment_end_matches_audio_duration():
    seq_json, _, _, _ = run_timeline(n_segments=3)
    segments = json.loads(seq_json)
    sr = 44100
    expected_end = round(len(DUMMY_Y) / sr, 2)
    assert segments[-1]["end_s"] == expected_end


def test_generate_subject_prompt_false_gives_empty_even_with_lyrics():
    _, _, _, subject_prompt = run_timeline(
        n_segments=2, lyrics="some lyrics", generate_subject_prompt=False
    )
    assert subject_prompt == ""
