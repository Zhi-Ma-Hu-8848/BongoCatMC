"""Touch crouch toggle, release and independent input regressions."""
import sys
sys.dont_write_bytecode = True
import unittest
from unittest.mock import Mock, patch
from test_native_touch import api, system


class SneakTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(system.time,'time',return_value=10.)
        clock.start()
        self.addCleanup(clock.stop)
        api.GetTopUI = lambda:'hud_screen'
        self.client = system.CatClient('test','client')
        self.client.loaded = True
        self.client.sneak_query = Mock()
        self.client.sneak_query.GetMolangValue.return_value = 0

    def stance(self, value):
        self.client.sneak_query.GetMolangValue.return_value = value
        self.client.update_sneak()
        return self.client.inputs.snapshot(10.2)

    def test_toggle_crouch_survives_finger_release_until_standing(self):
        self.assertEqual(self.stance(1)['art'],'Shift')
        self.client.touch_up()
        self.assertTrue(self.stance(1)['key'])
        self.assertFalse(self.stance(0)['key'])
        self.assertTrue(self.stance(1)['key'])
        self.assertFalse(self.stance(0)['key'])

    def test_menu_clear_then_restore_active_crouch(self):
        self.stance(1)
        self.client.menu_change({})
        api.GetTopUI = lambda:'inventory_screen'
        self.client.update_sneak()
        self.assertNotIn('sneak',self.client.inputs.keys)
        api.GetTopUI = lambda:'hud_screen'
        self.client.update_sneak()
        self.assertIn('sneak',self.client.inputs.keys)

    def test_no_repeat_steals_jump_and_standing_keeps_move(self):
        self.client.inputs.movement((0,1),9.)
        self.stance(1)
        self.client.jump_down({})
        count = self.client.inputs.events
        self.assertEqual(self.stance(1)['art'],'Space')
        self.assertEqual(self.client.inputs.events,count)
        self.client.jump_up()
        self.assertEqual(self.stance(1)['art'],'Shift')
        self.assertEqual(self.stance(0)['art'],'KeyW')
        self.assertTrue(self.stance(0)['key'])

    def test_physical_shift_and_mouse_are_independent(self):
        self.client.key({'key':'16','isDown':'1'})
        self.client.use_down({})
        self.stance(1)
        state = self.stance(0)
        self.assertTrue(state['key'])
        self.assertTrue(state['right'])
        self.assertIn('key:16',self.client.inputs.keys)

    def test_hidden_and_missing_query_do_not_latch(self):
        self.stance(1)
        self.client.enabled = False
        self.assertFalse(self.stance(1)['key'])
        self.client.enabled = True
        self.assertTrue(self.stance(1)['key'])
        self.assertFalse(self.stance(None)['key'])


if __name__=='__main__':unittest.main()
