"""Behavioral coverage for the native expression/motion menu and touch entry."""
import sys
sys.dont_write_bytecode = True
import unittest
from unittest.mock import Mock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon/behavior_pack'))
from bongocat_mod.client.effects import Effects, TapGesture, curve_value, cubic
from bongocat_mod.client.preferences import Preferences
from test_native_touch import api, system


class EffectsTests(unittest.TestCase):
    def test_preferences_sanitize_and_roundtrip(self):
        self.assertEqual(Preferences({'size':float('nan'),'transparency':'broken'}).data,{'size':1.,'flip_vertical':False,'flip_horizontal':False,'mouse_recenter':False,'position':None,'model':'default'})
        self.assertEqual(Preferences({'size':99.,'transparency':-10}).data,{'size':2.,'flip_vertical':False,'flip_horizontal':False,'mouse_recenter':False,'position':None,'model':'default'})
        prefs=Preferences({'transparency':.75});prefs.change('size',.75)
        self.assertFalse(prefs.change('transparency',.4))
        self.assertNotIn('transparency',prefs.data)
        self.assertEqual(Preferences(prefs.data).data,prefs.data)
        self.assertFalse(prefs.change('size',float('inf')))

    def test_mirrors_persist_and_ignore_non_boolean_config(self):
        prefs=Preferences({'size':1.25,'flip_horizontal':True,'flip_vertical':'false'})
        self.assertFalse(prefs.data['flip_vertical'])
        self.assertTrue(prefs.data['flip_horizontal'])
        self.assertFalse(prefs.change('flip_horizontal',.3))
        prefs.toggle('flip_vertical')
        self.assertTrue(prefs.dirty)
        self.assertEqual(Preferences(prefs.data).data,prefs.data)
        self.assertEqual(prefs.data['size'],1.25)

    def test_mouse_recenter_defaults_off_and_persists(self):
        prefs=Preferences({'size':1.3,'flip_horizontal':True})
        self.assertFalse(prefs.data['mouse_recenter'])
        prefs.toggle('mouse_recenter')
        self.assertTrue(Preferences(prefs.data).data['mouse_recenter'])
        self.assertEqual(prefs.data['size'],1.3)
        self.assertTrue(prefs.data['flip_horizontal'])

    def test_expression_fade_toggle_and_no_jump_on_switch(self):
        e=Effects();e.select('glasses',10.)
        self.assertEqual(e.sample(10.)[0][:2],(0.,0.))
        self.assertAlmostEqual(e.sample(10.4)[0][0],.5)
        before=e.sample(10.4)[0][:2]
        e.select('halo',10.4)
        self.assertEqual(e.sample(10.4)[0][:2],before)
        self.assertEqual(e.sample(12.)[0][:2],(0.,1.))
        e.select('halo',12.)
        self.assertEqual(e.expression,'default')
        self.assertEqual(e.sample(13.1)[0][:2],(0.,0.))

    def test_unrestricted_bezier_inverts_time_not_normalized_clock(self):
        t=.37
        clock=cubic(0.,.02,.12,1.,t)
        expected=cubic(0.,.7,.9,1.,t)
        result=curve_value([0,0,1,.02,.7,.12,.9,1,1],clock)
        self.assertAlmostEqual(result,expected,places=5)

    def test_linear_stepped_inverse_and_endpoints(self):
        self.assertEqual(curve_value([0,2,0,1,4],.5),3.)
        self.assertEqual(curve_value([0,2,2,1,4],.5),2.)
        self.assertEqual(curve_value([0,2,3,1,4],.5),4.)
        self.assertEqual(curve_value([0,2,2,1,4],1.),4.)

    def test_wave_original_peaks_finish_replay_stop(self):
        e=Effects();e.play('wave',10.)
        for t in (.4,1.167,1.967):
            self.assertAlmostEqual(e.sample(10.+t)[0][2],30.,places=4)
        self.assertEqual(e.sample(12.334)[0][2],0.)
        self.assertIsNone(e.motion)
        e.play('wave',20.);e.sample(20.4);e.play('wave',20.4)
        self.assertEqual(e.sample(20.4)[0][2],0.)
        e.stop();self.assertIsNone(e.motion)

    def test_flash_is_one_shot_and_expression_survives(self):
        e=Effects();e.select('halo',1.);e.play('flash',10.)
        vector,opacity=e.sample(10.5)
        self.assertEqual(vector[1],1.)
        self.assertGreater(opacity,.99)
        self.assertGreater(vector[3],.2)
        self.assertEqual(e.sample(11.634)[1],0.)
        self.assertIsNone(e.motion)
        self.assertEqual(e.expression,'halo')

    def test_touch_tap_drag_cancel_and_long_hold(self):
        t=TapGesture();a={'TouchId':1,'TouchPosX':10,'TouchPosY':20}
        t.down(a,1.);self.assertTrue(t.up(a,1.1,1.))
        t.down(a,2.);t.move(dict(a,TouchPosX=30),1.)
        self.assertFalse(t.up(a,2.1,1.))
        t.down(a,3.);t.cancel();self.assertFalse(t.up(a,3.1,1.))
        t.down(a,4.);self.assertFalse(t.up(a,5.,1.))


class MenuEntryTests(unittest.TestCase):
    def setUp(self):
        self.top='hud_screen'
        api.GetTopUI=lambda:self.top
        api.PushScreen=Mock(return_value=object())
        api.PopScreen=Mock()
        self.client=system.CatClient('test','client')
        self.client.ready=self.client.loaded=True

    def key(self, down):
        self.client.key({'key':'70','isDown':'1' if down else '0'})

    def test_f_open_once_close_on_next_press(self):
        self.key(True);self.key(True)
        api.PushScreen.assert_called_once_with('bongocatmc','menu')
        self.top='menu';self.key(False);self.key(True)
        api.PopScreen.assert_called_once()

    def test_f_does_not_open_over_inventory_or_loading(self):
        self.top='inventory_screen';self.key(True)
        api.PushScreen.assert_not_called()
        self.key(False);self.top='hud_screen';self.client.loaded=False
        self.key(True);api.PushScreen.assert_not_called()

    def test_menu_clears_inputs_and_restores_hidden_cat(self):
        self.client.inputs.key('test','KeyW',True,10.)
        self.client.enabled=False;self.client.open_menu()
        self.assertTrue(self.client.enabled)
        self.assertFalse(self.client.inputs.keys)

    def test_audio_stops_on_replace_and_stop(self):
        audio=Mock();self.client.audio=audio
        self.client.play_effect_motion('flash')
        audio.PlayCustomUIMusic.assert_called_once_with('bongocatmc.lightning',1.,1.,False)
        self.client.play_effect_motion('wave')
        self.assertEqual(audio.StopCustomMusic.call_count,2)
        self.assertEqual(self.client.effects.motion,'wave')
        self.client.stop_effect_motion()
        self.assertIsNone(self.client.effects.motion)
        self.assertEqual(audio.StopCustomMusic.call_count,3)


if __name__=='__main__':unittest.main()
