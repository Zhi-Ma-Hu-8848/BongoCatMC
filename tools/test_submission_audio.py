"""Check shipped audio, registry resolution, and common review-error regressions."""
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np
import soundfile as sf
from submission_audio import ROOT, check_audio, vorbis_info


class AudioTests(unittest.TestCase):
    def test_every_registered_sound_is_real_vorbis_with_allowed_bitrate(self):
        entries = check_audio(ROOT / 'addon/resource_pack')
        self.assertEqual(len(entries), 3)
        for info in entries.values():
            self.assertEqual(info['bitrate'], 96000)
            self.assertLessEqual(info['maximum_bitrate'], 128000)

    def test_originals_and_outputs_have_same_timing_channels_and_content(self):
        inputs = {
            'lightning': ROOT / 'assets/source/standard/live2d_motion1.flac',
            'deepseek_surprised': ROOT / 'assets/source/deepseek/img/standard/cat_model/Bingbingbing.mp3',
            'deepseek_hello': ROOT / 'assets/source/deepseek/img/standard/cat_model/Hello.mp3',
        }
        for name, source in inputs.items():
            with self.subTest(name=name):
                original, rate = sf.read(source, dtype='float32', always_2d=True)
                built, output_rate = sf.read(ROOT / 'addon/resource_pack/sounds/bongocatmc' / (name + '.ogg'), dtype='float32', always_2d=True)
                self.assertEqual(rate, output_rate)
                self.assertEqual(original.shape, built.shape)
                self.assertTrue(np.isfinite(built).all())
                self.assertGreater(float(np.corrcoef(original.ravel(), built.ravel())[0, 1]), .95)
                gain = float(np.linalg.norm(built) / np.linalg.norm(original))
                self.assertTrue(.9 < gain < 1.1, gain)

    def test_renamed_wav_is_not_accepted_as_ogg(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'renamed.ogg'
            file.write_bytes(b'RIFF' + bytes(40))
            with self.assertRaises(ValueError):
                vorbis_info(file)

    def test_header_over_128kbps_is_rejected(self):
        raw = bytearray((ROOT / 'addon/resource_pack/sounds/bongocatmc/lightning.ogg').read_bytes())
        marker = raw.index(b'\x01vorbis')
        struct.pack_into('<i', raw, marker + 20, 192000)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'high-bitrate.ogg'; file.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, '128 kbps'):
                vorbis_info(file)


if __name__ == '__main__':
    unittest.main()
