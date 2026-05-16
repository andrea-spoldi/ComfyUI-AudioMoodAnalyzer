import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, Mock
from audio_mood_analyzer import OllamaModelSelector


FAKE_TAGS_RESPONSE = {
    "models": [
        {"name": "qwen3:14b"},
        {"name": "hf.co/unsloth/Qwen3-4B-Instruct-2507-GGUF:UD-Q4_K_XL"},
        {"name": "llama3.2:3b"},
    ]
}


def _mock_get(url, **kwargs):
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.json = Mock(return_value=FAKE_TAGS_RESPONSE)
    return resp


def test_returns_newline_separated_model_names():
    node = OllamaModelSelector()
    with patch("audio_mood_analyzer.requests.get", side_effect=_mock_get):
        models_list, _ = node.list_models("http://localhost:11434")
    assert "qwen3:14b" in models_list
    assert "llama3.2:3b" in models_list
    assert models_list.count("\n") == 2  # 3 models → 2 newlines


def test_returns_first_model_as_second_output():
    node = OllamaModelSelector()
    with patch("audio_mood_analyzer.requests.get", side_effect=_mock_get):
        _, first_model = node.list_models("http://localhost:11434")
    assert first_model == "qwen3:14b"


def test_strips_trailing_slash_before_appending_tags():
    node = OllamaModelSelector()
    called_urls = []

    def capturing_get(url, **kwargs):
        called_urls.append(url)
        return _mock_get(url)

    with patch("audio_mood_analyzer.requests.get", side_effect=capturing_get):
        node.list_models("http://localhost:11434/")

    assert called_urls[0] == "http://localhost:11434/api/tags"


def test_handles_empty_model_list():
    node = OllamaModelSelector()

    def empty_get(url, **kwargs):
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json = Mock(return_value={"models": []})
        return resp

    with patch("audio_mood_analyzer.requests.get", side_effect=empty_get):
        models_list, first_model = node.list_models("http://localhost:11434")

    assert "(no models found)" in models_list
    assert first_model == ""


def test_handles_connection_error():
    node = OllamaModelSelector()

    with patch("audio_mood_analyzer.requests.get", side_effect=ConnectionError("refused")):
        models_list, first_model = node.list_models("http://localhost:11434")

    assert "error" in models_list.lower()
    assert first_model == ""
