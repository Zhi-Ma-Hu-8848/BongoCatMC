"""Prevent dark joins when white paw alpha edges filter over the white body."""
import unittest
import numpy as np
from PIL import Image
from build_cat import premultiply_rgba, ROOT, SRC, key_placements


class AlphaTests(unittest.TestCase):
    def test_white_edge_stays_white_when_bilinearly_filtered(self):
        source=Image.fromarray(np.array([[[255,255,255,255],[0,0,0,0]]],dtype=np.uint8))
        tex=np.asarray(premultiply_rgba(source),float)/255
        for weight in (.1,.25,.5,.75,.9):
            filtered=tex[0,0]*(1-weight)+tex[0,1]*weight
            composite=filtered[:3]+np.ones(3)*(1-filtered[3])
            np.testing.assert_allclose(composite,1.)

    def test_preserves_opacity_and_opaque_colours(self):
        raw=np.array([[[100,150,200,255],[100,150,200,128],[255,255,255,0]]],np.uint8)
        result=np.asarray(premultiply_rgba(Image.fromarray(raw)))
        np.testing.assert_array_equal(result[...,3],raw[...,3])
        np.testing.assert_array_equal(result[0,0],raw[0,0])
        np.testing.assert_array_equal(result[0,1],[50,75,100,128])
        np.testing.assert_array_equal(result[0,2],[0,0,0,0])

    def test_built_atlas_has_no_colour_exceeding_alpha(self):
        atlas=np.asarray(Image.open(ROOT/'addon/resource_pack/textures/models/bongocatmc/atlas.png'))
        self.assertTrue(np.all(atlas[...,:3]<=atlas[...,3:4]))

    def test_every_key_preserves_native_pixels_and_canvas_placement(self):
        keys=sorted((SRC/'resources/left-keys').glob('*.png'))
        atlas=Image.open(ROOT/'addon/resource_pack/textures/models/bongocatmc/atlas.png')
        meta=np.asarray(Image.open(ROOT/'addon/resource_pack/textures/models/bongocatmc/meta.png')).reshape(-1,4).astype(int)
        occupancy=np.zeros((2048,2048),bool)
        for i,(path,record) in enumerate(zip(keys,key_placements(keys))):
            source=Image.open(path).convert('RGBA')
            x,y=record['atlas_origin']; w,h=record['size']
            self.assertFalse(occupancy[y-2:y+h+2,x-2:x+w+2].any())
            occupancy[y-2:y+h+2,x-2:x+w+2]=True
            expected=premultiply_rgba(source.crop(record['canvas_bounds']))
            np.testing.assert_array_equal(np.asarray(atlas.crop((x,y,x+w,y+h))),np.asarray(expected),err_msg=path.stem)
            # Discarded pixels are alpha-zero; every nontransparent texel stays.
            self.assertEqual(np.count_nonzero(np.asarray(source)[...,3]),np.count_nonzero(np.asarray(expected)[...,3]))
            rows=meta[224*4+i*3:224*4+i*3+3]
            decoded=np.stack([rows[:,0]*256+rows[:,1],rows[:,2]*256+rows[:,3]],axis=1)
            np.testing.assert_array_equal(decoded,[record['atlas_origin'],record['canvas_bounds'][:2],record['size']])


if __name__=='__main__':unittest.main()
