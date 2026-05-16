import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
from audio_mood_analyzer import AnimateDiffScheduleFormatter


def make_segments(n=4, total_duration=18.0, prompt_prefix="prompt"):
    seg_dur = total_duration / n
    segments = []
    for i in range(n):
        start = round(i * seg_dur, 2)
        end = round((i + 1) * seg_dur, 2) if i < n - 1 else total_duration
        segments.append({
            "segment": i + 1,
            "start_s": start,
            "end_s": end,
            "mood_json": {},
            "environment_prompt": f"env {prompt_prefix} {i + 1}",
            "subject_prompt": f"subj {prompt_prefix} {i + 1}",
            "merge_prompt": f"merge {prompt_prefix} {i + 1}",
        })
    return segments


DUMMY_SEQ_4 = json.dumps(make_segments(4, 18.0))


def test_returns_n_lines_for_n_segments():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    lines = [l for l in schedule.split("\n") if l.strip()]
    assert len(lines) == 4


def test_every_line_has_quoted_frame_colon_quoted_prompt_format():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    for line in schedule.split("\n"):
        if line.strip():
            assert line.startswith('"'), f"Line does not start with quote: {line!r}"
            assert '": "' in line, f"Line missing separator: {line!r}"
            assert line.endswith('",'), f"Line does not end with trailing comma: {line!r}"


def test_first_line_is_always_frame_0():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    first_line = [l for l in schedule.split("\n") if l.strip()][0]
    assert first_line.startswith('"0":')


def test_first_frame_prompt_matches_segment_1_prompt():
    node = AnimateDiffScheduleFormatter()
    _, first_frame_prompt = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    assert first_frame_prompt == "merge prompt 1"


def test_frames_are_proportionally_distributed():
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(DUMMY_SEQ_4, 64, "merge_prompt")
    lines = [l for l in schedule.split("\n") if l.strip()]
    frames = [int(line.split('"')[1]) for line in lines]
    # 4 equal segments of 18s, total_frames=64:
    # seg1: 0/18*64=0, seg2: 4.5/18*64=16, seg3: 9/18*64=32, seg4: 13.5/18*64=48
    assert frames == [0, 16, 32, 48]


def test_empty_json_returns_empty_strings():
    node = AnimateDiffScheduleFormatter()
    schedule, first_frame_prompt = node.format_schedule("", 64, "merge_prompt")
    assert schedule == ""
    assert first_frame_prompt == ""


def test_invalid_json_returns_empty_strings():
    node = AnimateDiffScheduleFormatter()
    schedule, first_frame_prompt = node.format_schedule("not valid json", 64, "merge_prompt")
    assert schedule == ""
    assert first_frame_prompt == ""


def test_segments_with_empty_prompts_are_skipped():
    segments = make_segments(4, 18.0)
    segments[1]["merge_prompt"] = ""  # segment 2 has no merge prompt
    node = AnimateDiffScheduleFormatter()
    schedule, _ = node.format_schedule(json.dumps(segments), 64, "merge_prompt")
    lines = [l for l in schedule.split("\n") if l.strip()]
    assert len(lines) == 3  # segment 2 skipped


def test_prompt_type_environment_uses_environment_field():
    node = AnimateDiffScheduleFormatter()
    _, first_frame_prompt = node.format_schedule(DUMMY_SEQ_4, 64, "environment_prompt")
    assert first_frame_prompt == "env prompt 1"


def test_prompt_type_subject_uses_subject_field():
    node = AnimateDiffScheduleFormatter()
    _, first_frame_prompt = node.format_schedule(DUMMY_SEQ_4, 64, "subject_prompt")
    assert first_frame_prompt == "subj prompt 1"


def test_duplicate_frame_numbers_later_segment_wins():
    # Force a known collision: 2 segments with total_frames=1 means both map to frame 0.
    # Segment 2 is later and should win.
    segments = make_segments(2, 18.0)
    node = AnimateDiffScheduleFormatter()
    schedule, first_frame_prompt = node.format_schedule(json.dumps(segments), 1, "merge_prompt")
    # With total_frames=1, both segments map to frame 0 (clamped).
    # Segment 2's prompt ("merge prompt 2") should be in the output.
    assert "merge prompt 2" in schedule
    assert first_frame_prompt == "merge prompt 2"
