"""Direction mapping and continuous sampling regressions."""
import sys
sys.dont_write_bytecode = True
import unittest
from unittest.mock import Mock
from test_native_touch import NativeTouchTests, api, system
from bongocat_mod.client.input_state import InputState


class DirectionTests(unittest.TestCase):
    def test_cardinal_signs_and_diagonals(self):
        for vector, art in [((0,1),'KeyW'),((0,-1),'KeyS'),((1,0),'KeyA'),((-1,0),'KeyD'),
                            ((.9,.5),'KeyA'),((-.9,.5),'KeyD'),((.5,-.9),'KeyS'),((-.5,.9),'KeyW')]:
            state = InputState()
            state.movement(vector,1.)
            self.assertEqual(state.snapshot(1.1)['art'],art)

    def test_continuous_turn_without_stop_event(self):
        state = InputState()
        for index,(vector,art) in enumerate([((0,1),'KeyW'),((1,0),'KeyA'),((0,-1),'KeyS'),((-1,0),'KeyD')]):
            state.movement(vector,index+1.)
            self.assertEqual(state.snapshot(index+1.1)['art'],art)
        state.movement((0,0),6.)
        self.assertFalse(state.snapshot(6.1)['key'])

    def test_diagonal_hysteresis_then_deliberate_turn(self):
        state = InputState()
        state.movement((0,1),1.)
        for vector in ((.71,.70),(.70,.71),(.72,.69)):
            state.movement(vector,2.)
            self.assertEqual(state.snapshot(2.1)['art'],'KeyW')
        state.movement((.9,.4),3.)
        self.assertEqual(state.snapshot(3.1)['art'],'KeyA')
        state.movement((-.9,.4),4.)
        self.assertEqual(state.snapshot(4.1)['art'],'KeyD')

    def test_center_deadzone_and_missing_vector_release(self):
        state = InputState()
        state.movement((.08,.08),1.)
        self.assertFalse(state.snapshot(1.1)['key'])
        state.movement((1,0),2.)
        state.movement(None,3.)
        self.assertFalse(state.snapshot(3.1)['key'])

    def test_stable_poll_does_not_steal_jump_or_refresh_tap(self):
        state = InputState()
        state.movement((0,1),1.)
        state.key('jump','Space',True,2.)
        count = state.events
        state.movement((0,1),3.)
        self.assertEqual(state.events,count)
        self.assertEqual(state.snapshot(3.)['art'],'Space')
        state.key('jump','Space',False,4.)
        self.assertEqual(state.snapshot(4.)['art'],'KeyW')
        state.movement((0,0),5.)
        self.assertFalse(state.snapshot(5.)['key'])

    def test_physical_key_priority_survives_direction_change(self):
        state = InputState()
        state.key('key:65','KeyA',True,1.)
        state.movement((0,-1),2.)
        self.assertEqual(state.snapshot(2.)['art'],'KeyA')


class SamplingTests(unittest.TestCase):
    def setUp(self):
        api.GetTopUI = lambda:'hud_screen'
        self.client = system.CatClient('test','client')
        self.client.loaded = True
        self.client.motion = Mock()
        self.client.motion.GetInputVector.return_value = (0,1)
        self.client.sneak_query = Mock()
        self.client.sneak_query.GetMolangValue.return_value = 0

    def test_render_samples_direction_without_move_events(self):
        self.client.render({})
        self.assertEqual(self.client.inputs.keys['move'][1],'KeyW')
        self.client.motion.GetInputVector.return_value = (-1,0)
        self.client.render({})
        self.assertEqual(self.client.inputs.keys['move'][1],'KeyD')
        self.client.motion.GetInputVector.return_value = (0,0)
        self.client.render({})
        self.assertNotIn('move',self.client.inputs.keys)

    def test_menu_and_hidden_hud_clear_only_movement(self):
        self.client.render({})
        self.client.inputs.key('jump','Space',True,1.)
        api.GetTopUI = lambda:'inventory_screen'
        self.client.render({})
        self.assertNotIn('move',self.client.inputs.keys)
        self.assertIn('jump',self.client.inputs.keys)
        api.GetTopUI = lambda:'hud_screen'
        self.client.render({})
        self.client.enabled = False
        self.client.render({})
        self.assertNotIn('move',self.client.inputs.keys)


if __name__=='__main__':unittest.main()
