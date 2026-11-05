"""Model-specific input/effects, persistence and lossless asset boundaries."""
import json, sys, unittest
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addon/behavior_pack'))
from bongocat_mod.client.preferences import Preferences
from bongocat_mod.client.menu_catalog import entries_for
from bongocat_mod.client.deepseek_effects import DeepseekEffects, persistent
from bongocat_mod.client.deepseek_parameters import MOTIONS, KEY_ART, PARAMETERS, PHYSICS
from bongocat_mod.client.cubism_physics import Physics
from build_cat import premultiply_rgba

class ModelTests(unittest.TestCase):
    def test_old_preferences_migrate_and_unknown_model_is_rejected(self):
        self.assertEqual(Preferences({'size':1.2}).data['model'],'default')
        self.assertEqual(Preferences({'model':'missing'}).data['model'],'default')
        p=Preferences({'model':'deepseek','position':[.8,.2]})
        self.assertEqual(p.data['model'],'deepseek')
        self.assertEqual(p.data['position'],[.8,.2])

    def test_each_model_exposes_only_its_actions(self):
        self.assertEqual([e[0] for e in entries_for('default','motions')],['stop','flash','wave'])
        self.assertEqual(set(e[0] for e in entries_for('deepseek','motions')),set(MOTIONS)|{'stop'})
        self.assertEqual(len(entries_for('deepseek','expressions')),5)
        self.assertEqual(len(entries_for('deepseek','models')),2)

    def test_expression_fade_toggle_and_motion_stop(self):
        fx=DeepseekEffects();fx.select('Bowl',10)
        self.assertEqual(fx.expression_weights(10)['Bowl'],0.)
        self.assertAlmostEqual(fx.expression_weights(10.5)['Bowl'],.5)
        self.assertEqual(fx.expression_weights(11)['Bowl'],1.)
        fx.select('Bowl',11);self.assertIsNone(fx.expression)
        self.assertEqual(fx.expression_weights(12)['Bowl'],0.)
        for name,motion in MOTIONS.items():
            fx.stop();fx.play(name,20);values,playing=fx.motion_values(20.2)
            self.assertTrue(playing)
            self.assertTrue(values)
            fx.sample(20+motion['Meta']['Duration']+.001)
            self.assertEqual(fx.is_selected(name),persistent(motion))
            if persistent(motion):
                self.assertFalse(fx.play(name,40))
                self.assertFalse(fx.is_selected(name))

    def test_crossfade_preserves_previous_expression(self):
        fx=DeepseekEffects();fx.select('Bowl',10);fx.select('Glasses',12)
        self.assertEqual(fx.expression_weights(12)['Bowl'],1.)
        weights=fx.expression_weights(12.5)
        self.assertAlmostEqual(weights['Bowl'],.5);self.assertAlmostEqual(weights['Glasses'],.5)
        fx.select('StickyNotes',12.5)
        self.assertEqual(fx.expression_weights(12.5),weights)

    def test_preserved_actions_coexist_and_keyboard_stays_live(self):
        fx=DeepseekEffects();fx.play('Heart',1);fx.play('Sweat',2)
        state={'key':True,'art':'KeyW','left':True,'right':False}
        values=fx.frame(8,[.4,-.3],state)
        self.assertEqual(values['Hearting'],30);self.assertEqual(values['Sweat'],30)
        self.assertTrue(fx.overlay);self.assertEqual(values['ParamMouseLeftDown'],1.)
        fx.play('Sweat',9);values=fx.frame(9,[.4,-.3],state)
        self.assertEqual(values['Sweat'],0);self.assertEqual(values['Hearting'],30)
        fx.stop();values=fx.frame(10,[0,0],state);self.assertEqual(values['Hearting'],0)

    def test_packed_values_are_exact_float32_integers_and_pauses_stay_finite(self):
        fx=DeepseekEffects();state={'key':False,'art':'Space','left':False,'right':False}
        for i in range(90):fx.frame(i/60.,[1.,-1.],state)
        fx.frame(60,[0,0],state)
        vectors=fx.packed((1.,2.,3.,0.),state)
        for v in vectors[:2]+vectors[3:]:
            for x in v:self.assertEqual(float(np.float32(x)),x)
        for p in PARAMETERS:
            self.assertTrue(np.isfinite(fx.parameters[p['id']]))
            self.assertLessEqual(fx.parameters[p['id']],p['max'])
            self.assertGreaterEqual(fx.parameters[p['id']],p['min'])

    def test_live_physics_matches_cubism_variable_frame_reference(self):
        physics=Physics(PHYSICS,PARAMETERS)
        reference=json.loads((ROOT/'tools/fixtures/deepseek_physics_reference.json').read_text())
        for frame in reference:
            values={p['id']:p['default'] for p in PARAMETERS};values.update(frame['inputs'])
            physics.evaluate(values,frame['dt'])
            for key,wanted in frame['outputs'].items():self.assertAlmostEqual(values[key],wanted,delta=.0002)

    def test_registered_resource_links(self):
        rp=ROOT/'addon/resource_pack';registry=json.loads((rp/'models/netease_models.json').read_text())
        self.assertIn('bongocatmc_default',registry)
        entry=registry['bongocatmc_deepseek']
        for field in ('mesh','skeleton'):self.assertTrue((rp/'models'/entry[field]).is_file())
        for value in entry['texture'].values():self.assertTrue((rp/'textures/models'/(value+'.png')).is_file())

    def test_all_original_art_pixels_and_uv_regions_are_preserved(self):
        source=ROOT/'assets/source/deepseek/img/standard/cat_model'
        atlas=np.array(Image.open(ROOT/'addon/resource_pack/textures/models/bongocatmc_deepseek/atlas.png'))
        original=np.array(premultiply_rgba(Image.open(source/'deepseek.4096/texture_00.png')))
        records=json.loads((ROOT/'tools/fixtures/deepseek_keys.json').read_text())
        self.assertEqual(atlas.shape,original.shape)
        self.assertEqual(set(KEY_ART),set(p.stem for p in (source/'resources/left-keys').glob('*.png')))
        for record in records:
            im=Image.open(source/('resources/left-keys/'+record['name']+'.png')).crop(record['box'])
            x,y=record['origin'];w,h=record['size']
            np.testing.assert_array_equal(atlas[y:y+h,x:x+w],np.array(premultiply_rgba(im)))
            atlas[y:y+h,x:x+w]=original[y:y+h,x:x+w]
        np.testing.assert_array_equal(atlas,original)

if __name__=='__main__':unittest.main()
