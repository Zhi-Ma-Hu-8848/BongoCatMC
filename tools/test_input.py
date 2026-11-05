"""Input regressions, independent of the Minecraft VM."""
import sys
sys.dont_write_bytecode = True
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon/behavior_pack'))
from bongocat_mod.client.input_state import InputState, key_art


class InputTests(unittest.TestCase):
    def test_chord_release_preserves_other_key(self):
        state=InputState()
        state.key('key:87','KeyW',True,1.)
        state.key('key:32','Space',True,2.)
        self.assertEqual(state.snapshot(2.1)['art'],'Space')
        state.key('key:32','Space',False,3.)
        self.assertEqual(state.snapshot(3.1)['art'],'KeyW')
        self.assertTrue(state.snapshot(100.)['key'])
        state.key('key:87','KeyW',False,101.)
        self.assertFalse(state.snapshot(101.1)['key'])

    def test_quick_tap_has_visible_minimum(self):
        state=InputState()
        state.key('key:65','KeyA',True,1.)
        state.key('key:65','KeyA',False,1.01)
        self.assertTrue(state.snapshot(1.05)['key'])
        self.assertFalse(state.snapshot(1.11)['key'])

    def test_mouse_and_keyboard_are_independent(self):
        state=InputState()
        state.key('key:87','KeyW',True,1.)
        state.click('mouse',0,True,1.)
        state.click('mouse',1,True,1.)
        state.click('mouse',0,False,2.)
        self.assertEqual([state.snapshot(3.)[k] for k in ('key','left','right')],[True,False,True])

    def test_menu_clear_cancels_everything(self):
        state=InputState()
        state.key('move','KeyW',True,1.)
        state.click('touch',0,True,1.)
        state.clear()
        self.assertFalse(any(state.snapshot(1.01)[k] for k in ('key','left','right')))

    def test_mobile_source_does_not_override_physical_art(self):
        state=InputState()
        state.key('key:65','KeyA',True,1.)
        state.key('move','KeyW',True,1.1)
        self.assertEqual(state.snapshot(2.)['art'],'KeyA')
        state.key('key:65','KeyA',False,3.)
        self.assertEqual(state.snapshot(3.)['art'],'KeyW')

    def test_repeat_does_not_steal_latest_art(self):
        state=InputState()
        state.key('key:87','KeyW',True,1.)
        state.key('key:65','KeyA',True,2.)
        state.key('key:87','KeyW',True,3.)
        self.assertEqual(state.snapshot(4.)['art'],'KeyA')

    def test_mappings(self):
        self.assertEqual(key_art(87),'KeyW')
        self.assertEqual(key_art(32),'Space')
        self.assertIsNone(key_art(119))


if __name__=='__main__':unittest.main()
