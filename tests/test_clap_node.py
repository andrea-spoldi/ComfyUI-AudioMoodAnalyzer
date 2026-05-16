import sys, types, unittest
from unittest.mock import patch, MagicMock

# Import real torch now (before any stubbing) so tests can use real tensors.
# torch must be in sys.modules before the stub loop's "if not in" check.
import torch as _real_torch  # noqa

# Stub heavy dependencies before import
for mod in ["librosa", "soundfile", "numpy", "transformers"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import audio_mood_analyzer as ama

class TestResolveClapDevice(unittest.TestCase):
    def test_explicit_cpu(self):
        self.assertEqual(ama._resolve_clap_device("cpu"), "cpu")

    def test_explicit_cuda(self):
        self.assertEqual(ama._resolve_clap_device("cuda"), "cuda")

    def test_explicit_mps(self):
        self.assertEqual(ama._resolve_clap_device("mps"), "mps")

    def test_auto_resolves_cuda_first(self):
        with patch("torch.cuda.is_available", return_value=True), \
             patch("torch.backends.mps.is_available", return_value=True):
            self.assertEqual(ama._resolve_clap_device("auto"), "cuda")

    def test_auto_resolves_mps_when_no_cuda(self):
        with patch("torch.cuda.is_available", return_value=False), \
             patch("torch.backends.mps.is_available", return_value=True):
            self.assertEqual(ama._resolve_clap_device("auto"), "mps")

    def test_auto_resolves_cpu_fallback(self):
        with patch("torch.cuda.is_available", return_value=False), \
             patch("torch.backends.mps.is_available", return_value=False):
            self.assertEqual(ama._resolve_clap_device("auto"), "cpu")


class TestGetClapModel(unittest.TestCase):
    def setUp(self):
        ama._CLAP_MODEL_CACHE.clear()

    def test_loads_model_on_first_call(self):
        mock_model = MagicMock()
        mock_proc = MagicMock()
        with patch("transformers.ClapModel.from_pretrained", return_value=mock_model) as m_model, \
             patch("transformers.ClapProcessor.from_pretrained", return_value=mock_proc):
            model, proc = ama._get_clap_model("laion/clap-htsat-unfused", "cpu")
        m_model.assert_called_once_with("laion/clap-htsat-unfused")
        self.assertIs(model, mock_model)
        mock_model.to.assert_called_once_with("cpu")
        mock_model.eval.assert_called_once()
        self.assertIs(proc, mock_proc)

    def test_caches_model_on_second_call(self):
        mock_model = MagicMock()
        mock_proc = MagicMock()
        with patch("transformers.ClapModel.from_pretrained", return_value=mock_model) as m_model, \
             patch("transformers.ClapProcessor.from_pretrained", return_value=mock_proc):
            ama._get_clap_model("laion/clap-htsat-unfused", "cpu")
            ama._get_clap_model("laion/clap-htsat-unfused", "cpu")
        self.assertEqual(m_model.call_count, 1)

    def test_different_device_loads_separately(self):
        mock_model = MagicMock()
        mock_proc = MagicMock()
        with patch("transformers.ClapModel.from_pretrained", return_value=mock_model) as m_model, \
             patch("transformers.ClapProcessor.from_pretrained", return_value=mock_proc):
            ama._get_clap_model("laion/clap-htsat-unfused", "cpu")
            ama._get_clap_model("laion/clap-htsat-unfused", "cuda")
        self.assertEqual(m_model.call_count, 2)


import json

class TestClapAudioAnalyzer(unittest.TestCase):
    def _make_audio(self):
        mock_tensor = MagicMock()
        mock_tensor.detach.return_value.cpu.return_value.numpy.return_value = \
            [[[0.0] * 4800]]   # shape hint: list simulating [1, 1, 4800]
        return {"waveform": mock_tensor, "sample_rate": 48000}

    def test_input_types_has_required_audio(self):
        it = ama.ClapAudioAnalyzer.INPUT_TYPES()
        self.assertIn("audio", it["required"])

    def test_return_types(self):
        self.assertEqual(ama.ClapAudioAnalyzer.RETURN_TYPES, ("STRING", "STRING"))

    def test_return_names(self):
        self.assertEqual(ama.ClapAudioAnalyzer.RETURN_NAMES, ("clap_json", "semantic_summary"))

    def test_category(self):
        self.assertEqual(ama.ClapAudioAnalyzer.CATEGORY, "audio/analysis")

    def test_function_name(self):
        self.assertEqual(ama.ClapAudioAnalyzer.FUNCTION, "analyze")

    def test_error_path_returns_empty_summary(self):
        node = ama.ClapAudioAnalyzer()
        audio = self._make_audio()
        with patch.object(ama, "_get_clap_model", side_effect=RuntimeError("model load failed")), \
             patch.object(ama, "_resolve_clap_device", return_value="cpu"):
            clap_json, semantic_summary = node.analyze(
                audio, "laion/clap-htsat-unfused", "cpu", "dark atmospheric tension"
            )
        data = json.loads(clap_json)
        self.assertTrue(data["enabled"])
        self.assertIn("error", data)
        self.assertEqual(data["fallback"], "librosa_only")
        self.assertEqual(semantic_summary, "")

    def test_fewer_than_3_anchors_returns_all_in_inference(self):
        node = ama.ClapAudioAnalyzer()
        audio = self._make_audio()
        anchors = "dark atmospheric tension\nnocturnal fear"

        import torch as real_torch
        a = real_torch.tensor([[1.0, 0.0]])
        t = real_torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        mock_model = MagicMock()
        mock_model.get_audio_features.return_value = a
        mock_model.get_text_features.return_value = t
        mock_proc = MagicMock()
        mock_proc.return_value = {}

        import contextlib
        with patch.object(ama, "_get_clap_model", return_value=(mock_model, mock_proc)), \
             patch.object(ama, "_resolve_clap_device", return_value="cpu"), \
             patch("torch.no_grad", return_value=contextlib.nullcontext()):
            clap_json, _ = node.analyze(audio, "laion/clap-htsat-unfused", "cpu", anchors)

        data = json.loads(clap_json)
        self.assertEqual(len(data["semantic_inference"]), 2)

    def test_happy_path_top3_and_summary_prefix(self):
        node = ama.ClapAudioAnalyzer()
        audio = self._make_audio()
        anchors = "dark atmospheric tension\nnocturnal fear\nfragile human vulnerability"

        import torch as real_torch
        # audio_emb aligns with first anchor
        a = real_torch.tensor([[1.0, 0.0, 0.0]])
        t = real_torch.tensor([[1.0, 0.0, 0.0],
                                [0.0, 1.0, 0.0],
                                [0.0, 0.0, 1.0]])
        mock_model = MagicMock()
        mock_model.get_audio_features.return_value = a
        mock_model.get_text_features.return_value = t
        mock_proc = MagicMock()
        mock_proc.return_value = {}

        import contextlib
        with patch.object(ama, "_get_clap_model", return_value=(mock_model, mock_proc)), \
             patch.object(ama, "_resolve_clap_device", return_value="cpu"), \
             patch("torch.no_grad", return_value=contextlib.nullcontext()):
            clap_json, semantic_summary = node.analyze(
                audio, "laion/clap-htsat-unfused", "cpu", anchors
            )

        data = json.loads(clap_json)
        self.assertTrue(data["enabled"])
        self.assertIn("top_text_matches", data)
        self.assertEqual(len(data["semantic_inference"]), 3)
        self.assertEqual(data["semantic_inference"][0], "dark atmospheric tension")
        self.assertTrue(semantic_summary.startswith("CLAP: "))
        self.assertIn("dark atmospheric tension", semantic_summary)

    def test_registered_in_node_class_mappings(self):
        self.assertIn("ClapAudioAnalyzer", ama.NODE_CLASS_MAPPINGS)
        self.assertIs(ama.NODE_CLASS_MAPPINGS["ClapAudioAnalyzer"], ama.ClapAudioAnalyzer)

    def test_registered_in_display_name_mappings(self):
        self.assertIn("ClapAudioAnalyzer", ama.NODE_DISPLAY_NAME_MAPPINGS)
        self.assertEqual(ama.NODE_DISPLAY_NAME_MAPPINGS["ClapAudioAnalyzer"], "CLAP Audio Analyzer")
