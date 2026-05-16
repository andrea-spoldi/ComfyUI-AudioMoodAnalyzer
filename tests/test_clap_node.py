import sys, types, unittest
from unittest.mock import patch, MagicMock

# Stub heavy dependencies before import
for mod in ["librosa", "soundfile", "numpy", "torch", "transformers"]:
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
