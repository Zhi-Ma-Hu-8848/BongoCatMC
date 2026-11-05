"""Regress native lazy model creation without requiring a foreground game."""
import sys
sys.dont_write_bytecode = True
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon/behavior_pack'))
from bongocat_mod.client.input_state import InputState


class LazyDoll(object):
    def __init__(self):
        self.visible = True
        self.requested = False
        self.native = -1

    def SetVisible(self, visible):
        self.visible = visible

    def SetTouchEnable(self, enabled): pass
    def SetSize(self, size): pass
    def SetPosition(self, position): pass
    def asNeteasePaperDoll(self): return self

    def RenderSkeletonModel(self, options):
        self.requested = True
        return True

    def GetModelId(self): return self.native

    def native_render(self):
        if self.visible and self.requested:
            self.native = 7


class Screen(object):
    def __init__(self, *args):
        self.test_actor = LazyDoll()
        self.test_root = Mock()
        self.test_root.GetSize.return_value = (480.,276.)

    def GetBaseUIControl(self, path):
        return self.test_actor if path == '/root/actor' else self.test_root

    def UpdateScreen(self, force): pass


api = types.ModuleType('mod.client.extraClientApi')
api.GetScreenNodeCls = lambda: Screen
modules = {'mod':types.ModuleType('mod'),'mod.client':types.ModuleType('mod.client'),
           'mod.client.extraClientApi':api}
with patch.dict(sys.modules, modules):
    from bongocat_mod.client.hud import CatHud


class HudStartupTests(unittest.TestCase):
    def setUp(self):
        self.owner = Mock(enabled=True,inputs=InputState())
        self.owner.gameplay.return_value = True
        factory = Mock()
        factory.CreateRot.return_value.GetRot.return_value = (0.,0.)
        factory.CreateModel.return_value.SetExtraUniformValue.return_value = True
        api.GetSystem = lambda *args: self.owner
        api.GetEngineCompFactory = lambda: factory
        api.GetLevelId = lambda: 'level'
        api.GetLocalPlayerId = lambda: 'player'
        api.GetTopUI = lambda: 'hud_screen' if self.owner.gameplay() else 'inventory_screen'
        self.hud = CatHud('test','hud',{})
        self.hud.Create()

    def frame(self):
        self.hud.last = 0.
        self.hud.render_frame()
        self.hud.test_actor.native_render()

    def assert_ready(self):
        self.assertTrue(self.hud.test_actor.visible)
        self.assertEqual(self.hud.model,7)
        self.assertEqual(len(self.hud.sent),3)

    def test_fresh_hud_bootstraps_visible_native_pass(self):
        self.frame()
        self.frame()
        self.assert_ready()

    def test_start_in_menu_then_return(self):
        self.owner.gameplay.return_value = False
        self.frame()
        self.assertFalse(self.hud.test_actor.visible)
        self.assertEqual(self.hud.model,-1)
        self.owner.gameplay.return_value = True
        self.frame()
        self.frame()
        self.assert_ready()

    def test_hidden_before_first_load_then_enabled(self):
        self.owner.enabled = False
        self.frame()
        self.assertEqual(self.hud.model,-1)
        self.owner.enabled = True
        self.frame()
        self.frame()
        self.assert_ready()


if __name__ == '__main__': unittest.main()
