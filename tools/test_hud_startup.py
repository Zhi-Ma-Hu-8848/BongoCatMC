"""Regress native lazy model creation without requiring a foreground game."""
import sys
sys.dont_write_bytecode = True
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon/behavior_pack'))
from bongocat_mod.client.input_state import InputState
from bongocat_mod.client.effects import Effects
from bongocat_mod.client.preferences import Preferences


class LazyDoll(object):
    def __init__(self):
        self.visible = True
        self.requested = False
        self.native = -1

    def SetVisible(self, visible):
        self.visible = visible

    def SetTouchEnable(self, enabled): pass
    def SetSize(self, size): pass
    def SetPosition(self, position): self.position = position
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
        self.test_root.GetGlobalPosition.return_value = (32.,96.)
        self.test_root.asScrollView.return_value.GetScrollViewContentPath.return_value = '/scroll_content'
        self.test_root.asScrollView.return_value.GetScrollViewPos.return_value = 0.

    def GetBaseUIControl(self, path):
        return self.test_actor if path == '/root/actor' else self.test_root

    def UpdateScreen(self, force): pass


api = types.ModuleType('mod.client.extraClientApi')
api.GetScreenNodeCls = lambda: Screen
class Binder:
    BF_BindInt=1;BF_BindBool=2;BF_BindFloat=4;BF_SliderChanged=8;BF_SliderFinished=16
    @staticmethod
    def binding(*args):return lambda function:function
api.GetViewBinderCls = lambda: Binder
api.GetViewViewRequestCls = lambda: types.SimpleNamespace(Refresh=1)
modules = {'mod':types.ModuleType('mod'),'mod.client':types.ModuleType('mod.client'),
           'mod.client.extraClientApi':api}
with patch.dict(sys.modules, modules):
    from bongocat_mod.client.hud import CatHud
    from bongocat_mod.client.menu import CatMenu


class HudStartupTests(unittest.TestCase):
    def setUp(self):
        self.owner = Mock(enabled=True,inputs=InputState())
        self.owner.effects = Effects()
        self.owner.preferences = Preferences()
        self.owner.menu = None
        self.owner.gameplay.return_value = True
        factory = Mock()
        factory.CreateRot.return_value.GetRot.return_value = (0.,0.)
        factory.CreateActorMotion.return_value.GetMousePosition.return_value = None
        factory.CreateGame.return_value.GetScreenSize.return_value = (1440.,828.)
        self.factory = factory
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
        self.assertEqual(len(self.hud.sent),4)

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

    def test_menu_has_own_live_preview_without_duplicate_hud(self):
        menu = CatMenu('test','menu',{})
        menu.Create()
        self.owner.gameplay.return_value = False
        menu.Update()
        menu.test_actor.native_render()
        menu.last = 0.
        menu.Update()
        self.assertEqual(menu.model,7)
        self.assertEqual(len(menu.sent),4)
        self.frame()
        self.assertFalse(self.hud.visible)
        menu.Destroy()
        self.assertIsNone(self.owner.menu)
        self.owner.gameplay.return_value = True
        self.frame();self.frame()
        self.assert_ready()

    def test_dropdown_toggle_switch_and_background_keeps_panel(self):
        menu = CatMenu('test','menu',{});menu.Create()
        menu.toolbar_action('motions')({})
        self.assertEqual(menu.expanded,'motions')
        menu.toolbar_action('expressions')({})
        self.assertEqual(menu.expanded,'expressions')
        menu.toolbar_action('expressions')({})
        self.assertIsNone(menu.expanded)
        menu.toolbar_action('motions')({});menu.toolbar_action('outside')({})
        self.assertEqual(menu.expanded,'motions')
        menu.toolbar_action('settings')({});menu.toolbar_action('outside')({})
        self.assertEqual(menu.expanded,'settings')
        self.owner.close_menu.assert_not_called()

    def test_dropdown_stops_correct_system_and_dismisses(self):
        menu = CatMenu('test','menu',{});menu.Create()
        self.owner.effects.select('halo',1.)
        self.owner.effects.play('wave',1.)
        menu.expanded = 'expressions';menu.choose('expressions','stop')
        self.assertIsNone(self.owner.effects.expression)
        self.assertEqual(self.owner.effects.motion,'wave')
        self.assertIsNone(menu.expanded)
        menu.choose('motions','stop')
        self.owner.stop_effect_motion.assert_called_once()

    def test_scroll_drag_never_plays_a_row(self):
        menu = CatMenu('test','menu',{});menu.Create()
        a = {'TouchId':1,'TouchPosX':10,'TouchPosY':50}
        menu.row_callback('motions','flash','down')(a)
        menu.row_callback('motions','flash','move')(dict(a,TouchPosY=80))
        menu.row_callback('motions','flash','up')(a)
        self.owner.play_effect_motion.assert_not_called()
        menu.row_callback('motions','flash','down')(a)
        menu.row_callback('motions','flash','up')(a)
        self.owner.play_effect_motion.assert_called_once_with('flash')

    def test_slider_previews_then_commits_and_keeps_default_anchor(self):
        menu = CatMenu('test','menu',{});menu.Create()
        menu.expanded='settings'
        menu.size_slider.down({'TouchId':1,'TouchPosX':600.,'TouchPosY':100.})
        self.owner.save_preferences.assert_not_called()
        self.assertEqual(self.owner.preferences.data['size'],2.)
        self.frame();self.frame()
        zoom,x,y,mirror = self.hud.sent[3]
        base=.72*self.hud.scale
        self.assertAlmostEqual(zoom,base*2)
        self.assertAlmostEqual(x+24*zoom*306/354.,24*base*306/354.)
        self.assertAlmostEqual(y-12*zoom,8*self.hud.scale-12*base)
        self.assertEqual(mirror,0.)
        menu.size_slider.up({'TouchId':1,'TouchPosX':0.,'TouchPosY':0.})
        self.owner.save_preferences.assert_called_once()

    def test_mirror_switches_combine_and_keep_settings_open(self):
        menu=CatMenu('test','menu',{});menu.Create();menu.expanded='settings'
        for key,expected in [('flip_horizontal',1.),('flip_vertical',3.),('flip_horizontal',2.),('flip_vertical',0.)]:
            menu.choose('settings',key)
            self.frame();self.frame()
            self.assertEqual(self.hud.sent[3][3],expected)
            self.assertEqual(menu.expanded,'settings')
        self.assertEqual(self.owner.save_preferences.call_count,4)
        # A vertical swipe over a switch must scroll, not toggle it.
        a={'TouchId':2,'TouchPosX':200.,'TouchPosY':50.}
        menu.row_callback('settings','flip_vertical','down')(a)
        menu.row_callback('settings','flip_vertical','move')(dict(a,TouchPosY=90.))
        menu.row_callback('settings','flip_vertical','up')(a)
        self.assertFalse(self.owner.preferences.data['flip_vertical'])

    def test_mouse_recenter_switch_preserves_pose_when_off(self):
        self.hud.follow(.05)
        self.hud.rot.GetRot.return_value=(10.,20.)
        self.hud.follow(.05)
        target=list(self.hud.target)
        self.assertNotEqual(target,[2.,2.])
        for unused in range(100):self.hud.follow(.05)
        self.assertEqual(self.hud.target,target)
        menu=CatMenu('test','menu',{});menu.Create();menu.expanded='settings'
        menu.choose('settings','mouse_recenter')
        for unused in range(100):self.hud.follow(.05)
        for value in self.hud.target:self.assertAlmostEqual(value,2.,places=5)
        self.assertEqual(menu.expanded,'settings')
        menu.choose('settings','mouse_recenter')
        self.hud.rot.GetRot.return_value=(20.,40.)
        self.hud.follow(.05)
        target=list(self.hud.target)
        for unused in range(100):self.hud.follow(.05)
        self.assertEqual(self.hud.target,target)

    def test_hidden_settings_ignore_late_slider_events(self):
        menu = CatMenu('test','menu',{});menu.Create()
        menu.size_slider.down({'TouchId':1,'TouchPosX':600.,'TouchPosY':100.})
        menu.size_slider.up({'TouchId':1,'TouchPosX':0.,'TouchPosY':0.})
        self.assertEqual(self.owner.preferences.data['size'],1.)
        self.owner.save_preferences.assert_not_called()

    def test_touch_overrun_release_and_other_finger(self):
        menu = CatMenu('test','menu',{});menu.Create();menu.expanded='settings'
        slider = menu.size_slider
        slider.down({'TouchId':1,'TouchPosX':100.,'TouchPosY':100.})
        for x in (300.,600.,900.):
            slider.move({'TouchId':1,'TouchPosX':x,'TouchPosY':100.})
        self.assertEqual(self.owner.preferences.data['size'],2.)
        slider.move({'TouchId':2,'TouchPosX':0.,'TouchPosY':0.})
        slider.up({'TouchId':2,'TouchPosX':0.,'TouchPosY':0.})
        self.assertEqual(slider.touch,1)
        slider.up({'TouchId':1,'TouchPosX':0.,'TouchPosY':0.})
        self.assertEqual(self.owner.preferences.data['size'],2.)
        self.owner.save_preferences.assert_called_once()
        slider.move({'TouchId':1,'TouchPosX':0.,'TouchPosY':0.})
        self.assertEqual(self.owner.preferences.data['size'],2.)

    def test_touch_can_drag_back_and_cancel_keeps_last_position(self):
        menu = CatMenu('test','menu',{});menu.Create();menu.expanded='settings'
        slider = menu.size_slider
        slider.down({'TouchId':1,'TouchPosX':600.,'TouchPosY':100.})
        for x in (400.,200.,-100.):
            slider.move({'TouchId':1,'TouchPosX':x,'TouchPosY':100.})
        slider.cancel({'TouchId':1,'TouchPosX':0.,'TouchPosY':0.})
        self.assertEqual(self.owner.preferences.data['size'],.5)
        self.assertIsNone(slider.touch)
        self.owner.save_preferences.assert_called_once()

    def test_mouse_up_zero_coordinates_uses_real_cursor(self):
        menu = CatMenu('test','menu',{});menu.Create();menu.expanded='settings'
        cursor=self.factory.CreateActorMotion.return_value.GetMousePosition
        cursor.return_value=(300.,300.)
        slider=menu.size_slider
        slider.down({'TouchId':0,'TouchPosX':100.,'TouchPosY':100.})
        self.assertEqual(slider.mouse_scale,(1./3,1./3))
        cursor.return_value=(1800.,300.)
        slider.poll()
        self.assertEqual(self.owner.preferences.data['size'],2.)
        # Replay the observed release sequence: two zero moves followed by Up.
        for unused in range(2):
            slider.move({'TouchId':0,'TouchPosX':0.,'TouchPosY':0.})
        slider.up({'TouchId':0,'TouchPosX':0.,'TouchPosY':0.})
        self.assertEqual(self.owner.preferences.data['size'],2.)
        self.owner.save_preferences.assert_called_once()

    def test_slider_updates_do_not_force_screen_layout(self):
        menu = CatMenu('test','menu',{});menu.Create();menu.expanded='settings'
        menu.refresh()
        menu.UpdateScreen=Mock()
        menu.size_slider.down({'TouchId':1,'TouchPosX':600.,'TouchPosY':100.})
        menu.refresh()
        menu.UpdateScreen.assert_not_called()


if __name__ == '__main__': unittest.main()
