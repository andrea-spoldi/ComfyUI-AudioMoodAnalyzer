import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from audio_mood_analyzer import _build_style_block

def test_known_preset_returns_preset_text():
    result = _build_style_block("painterly", "")
    assert "Francis Bacon" in result
    assert result.strip()

def test_preset_plus_notes_appends_notes():
    result = _build_style_block("painterly", "cold palette, morning light")
    assert "Francis Bacon" in result
    assert "cold palette, morning light" in result

def test_custom_preset_empty_notes_returns_empty():
    result = _build_style_block("custom", "")
    assert result == ""

def test_custom_preset_with_notes_returns_notes_only():
    result = _build_style_block("custom", "my own direction")
    assert result == "my own direction"
    assert "Francis Bacon" not in result

def test_unknown_preset_falls_back_to_empty():
    result = _build_style_block("nonexistent", "")
    assert result == ""
