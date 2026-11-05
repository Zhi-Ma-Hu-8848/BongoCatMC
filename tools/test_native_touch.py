"""Exercise actual client handlers with native use-button release sequences."""
import sys
sys.dont_write_bytecode = True
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon/behavior_pack'))


class ClientBase(object):
    def __init__(self, *args): pass
    def ListenForEvent(self, *args): pass


api = types.ModuleType('mod.client.extraClientApi')
api.GetClientSystemCls = lambda: ClientBase
api.GetEngineNamespace = lambda: 'Minecraft'
api.GetEngineSystemName = lambda: 'Engine'
modules = {'mod':types.ModuleType('mod'),'mod.client':types.ModuleType('mod.client'),
           'mod.client.extraClientApi':api}
with patch.dict(sys.modules, modules):
    from bongocat_mod.client import system


class NativeTouchTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(system.time,'time',return_value=10.)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        api.GetTopUI = lambda: 'hud_screen'
        self.client = system.CatClient('test','client')

    def state(self):
        # Advance past the intentional 100 ms minimum visible tap.
        return self.client.inputs.snapshot(10.2)

    def test_virtual_use_repeated_press_and_touch_release(self):
        for _ in range(5):
            args = {}
            self.client.use_down(args)
            self.assertTrue(self.state()['right'])
            self.client.touch_up()
            self.assertFalse(self.state()['right'])
            self.assertEqual(args,{})  # Never cancels the game's real use action.

    def test_release_still_works_after_menu_opens(self):
        self.client.use_down({})
        api.GetTopUI = lambda: 'inventory_screen'
        self.client.touch_up({})
        self.assertFalse(self.state()['right'])

    def test_pc_release_then_touch_release_is_idempotent(self):
        self.client.use_down({})
        self.client.use_up()
        self.client.touch_up()
        self.client.touch_up()
        self.assertFalse(self.state()['right'])

    def test_release_preserves_other_sources_and_keyboard(self):
        self.client.key({'key':'87','isDown':'1'})
        self.client.inputs.click('independent',1,True,10.)
        self.client.attack_down({})
        self.client.use_down({})
        self.client.touch_up()
        self.assertEqual(self.client.inputs.mouse[1],{'independent'})
        self.assertTrue(self.state()['key'])
        self.assertTrue(self.state()['left'])
        self.assertTrue(self.state()['right'])

    def test_hold_attack_and_native_use_both_release(self):
        self.client.hold({})
        self.client.use_down({})
        self.client.touch_up()
        self.assertFalse(self.state()['left'])
        self.assertFalse(self.state()['right'])

    def test_duplicate_key_and_native_press_share_one_source(self):
        self.client.key({'key':'-98','isDown':'1'})
        self.client.use_down({})
        self.client.touch_up()
        self.assertFalse(self.state()['right'])
        self.client.key({'key':'-98','isDown':'0'})
        self.assertFalse(self.state()['right'])


if __name__ == '__main__': unittest.main()
