"""Check packed shader payload, moving masks, and submission audio timing."""
import json
import unittest
import numpy as np
import soundfile as sf
from PIL import Image
from build_cat import ROOT, RP, SRC


class EffectAssetTests(unittest.TestCase):
    def test_packed_vertices_and_opacity_match_core(self):
        model=json.loads((ROOT/'build/model.json').read_text())
        n=model['vertexCount'];nd=len(model['drawables']);count=model['poseCount']
        original=np.fromfile(ROOT/'build/poses.f32',dtype='<f4').reshape(count,model['stride'])
        stride=n+nd+sum(d['vertexCount'] for d in model['drawables'] if d['masks'])
        packed=np.asarray(Image.open(RP/'textures/models/bongocatmc/poses.png')).reshape(-1,4)[:count*stride].reshape(count,stride,4).astype(np.uint32)
        decoded=np.stack([packed[:,:,0]*256+packed[:,:,1],packed[:,:,2]*256+packed[:,:,3]],axis=-1)/65535.
        np.testing.assert_allclose(decoded[:,:n]*8-4,original[:,:n*2].reshape(count,n,2),atol=4/65535.+1e-8,rtol=0)
        # Core may overshoot 1 slightly; render opacity is necessarily clamped.
        np.testing.assert_allclose(decoded[:,n:n+nd,0],np.clip(original[:,n*2:n*2+nd],0,1),atol=.5/65535.+1e-8,rtol=0)

    def test_moving_masks_inherit_effect_and_metadata(self):
        model=json.loads((ROOT/'build/model.json').read_text());ds=model['drawables']
        meta=np.asarray(Image.open(RP/'textures/models/bongocatmc/meta.png')).reshape(-1,4)
        offset=0
        for d in ds:
            self.assertTrue(np.all(meta[offset*4+1:(offset+d['vertexCount'])*4:4,3]==d['effect']))
            for mask in d['masks']:
                if ds[mask]['effect']:
                    self.assertEqual(d['effect'],ds[mask]['effect'])
            offset+=d['vertexCount']
        self.assertEqual(next(d['effect'] for d in ds if d['id']=='ArtMesh17'),1)

    def test_sound_preserves_timing_and_channels_in_submission_format(self):
        from submission_audio import vorbis_info
        path=RP/'sounds/bongocatmc/lightning.ogg'
        self.assertEqual(vorbis_info(path)['bitrate'],96000)
        source,rate=sf.read(SRC/'live2d_motion1.flac',dtype='float32')
        built,output_rate=sf.read(path,dtype='float32')
        self.assertEqual(rate,output_rate)
        self.assertEqual(source.shape,built.shape)
        self.assertGreater(float(np.corrcoef(source.ravel(),built.ravel())[0,1]),.95)


if __name__=='__main__':unittest.main()
