"""Long hold, pointer ownership, saved bounds, and tap/drag separation."""
import unittest
from unittest.mock import patch
import test_hud_startup as startup
from bongocat_mod.client.preferences import Preferences


class HudDragTests(unittest.TestCase):
    setUp = startup.HudStartupTests.setUp
    frame = startup.HudStartupTests.frame

    def start(self, clock):
        clock.return_value=10.
        self.frame();self.frame()
        self.point={'TouchId':1,'TouchPosX':self.hud.touch_position[0]+20.,
                    'TouchPosY':self.hud.touch_position[1]+15.}
        self.hud.touch_down(self.point)

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_short_tap_and_early_swipe(self, clock):
        self.start(clock)
        clock.return_value=10.2
        self.hud.touch_up(self.point)
        self.owner.open_menu.assert_called_once()
        self.assertIsNone(self.owner.preferences.data['position'])
        self.owner.open_menu.reset_mock()
        self.start(clock)
        clock.return_value=10.1
        self.hud.touch_move(dict(self.point,TouchPosX=self.point['TouchPosX']-40))
        clock.return_value=10.7
        self.hud.touch_up(self.point)
        self.owner.open_menu.assert_not_called()
        self.assertIsNone(self.owner.preferences.data['position'])

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_hold_drag_moves_art_and_target_and_saves(self, clock):
        self.start(clock)
        origin=self.hud.touch_position
        actor=self.hud.test_actor.position
        clock.return_value=10.6
        self.hud.touch_move(dict(self.point,TouchPosX=self.point['TouchPosX']-80,TouchPosY=self.point['TouchPosY']-40))
        for i,delta in enumerate((-80,-40)):
            self.assertAlmostEqual(self.hud.touch_position[i]-origin[i],delta,places=3)
            self.assertAlmostEqual(self.hud.test_actor.position[i]-actor[i],delta,places=3)
        saved=list(self.owner.preferences.data['position'])
        self.hud.touch_up(dict(self.point,TouchId=2,TouchPosX=0,TouchPosY=0))
        self.assertIsNotNone(self.hud.drag.press)
        self.hud.touch_up(dict(self.point,TouchPosX=0,TouchPosY=0))
        self.assertEqual(self.owner.preferences.data['position'],saved)
        self.owner.open_menu.assert_not_called()
        self.owner.save_preferences.assert_called_once()
        self.assertEqual(Preferences(self.owner.preferences.data).data['position'],saved)

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_drag_back_to_origin_and_bounds_on_resize(self, clock):
        self.start(clock)
        origin=self.hud.touch_position
        clock.return_value=10.6
        self.hud.touch_move(dict(self.point,TouchPosX=0.,TouchPosY=0.))
        self.hud.touch_move(self.point)
        for i in (0,1):self.assertAlmostEqual(self.hud.touch_position[i],origin[i],places=3)
        self.hud.touch_move(dict(self.point,TouchPosX=10000.,TouchPosY=-10000.))
        self.assertEqual(self.owner.preferences.data['position'],[1.,0.])
        self.hud.touch_cancel(self.point)
        self.owner.save_preferences.assert_called_once()
        self.hud.test_root.GetSize.return_value=(320.,200.)
        self.hud.layout()
        for i in (0,1):
            self.assertGreaterEqual(self.hud.touch_position[i],6.)
            self.assertLessEqual(self.hud.touch_position[i]+self.hud.touch_size[i],self.hud.size[i]-6.)

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_mouse_units_and_zero_release(self, clock):
        self.start(clock)
        self.hud.touch_cancel(self.point)
        cursor=self.factory.CreateActorMotion.return_value.GetMousePosition
        cursor.return_value=(self.point['TouchPosX']*3,self.point['TouchPosY']*3)
        self.hud.touch_down(self.point)
        self.assertEqual(self.hud.drag.scale,(1./3,1./3))
        clock.return_value=10.6
        cursor.return_value=((self.point['TouchPosX']-60)*3,(self.point['TouchPosY']-30)*3)
        self.hud.drag.update(10.6)
        saved=list(self.owner.preferences.data['position'])
        self.hud.touch_up(dict(self.point,TouchPosX=0.,TouchPosY=0.))
        self.assertEqual(self.owner.preferences.data['position'],saved)
        self.owner.open_menu.assert_not_called()
        self.owner.save_preferences.assert_called_once()

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_mobile_polling_without_move_callbacks_and_release_zero(self, clock):
        self.start(clock);self.hud.touch_cancel(self.point)
        with patch.object(startup.api,'GetTouchPos',create=True) as touch:
            touch.return_value=tuple(self.point[k]*3 for k in ('TouchPosX','TouchPosY'))
            self.hud.touch_down(self.point)
            origin=self.hud.touch_position
            clock.return_value=10.6
            touch.return_value=((self.point['TouchPosX']-70)*3,(self.point['TouchPosY']-30)*3)
            self.hud.drag.update(10.6)
            self.assertAlmostEqual(self.hud.touch_position[0],origin[0]-70,places=3)
            saved=list(self.owner.preferences.data['position'])
            touch.return_value=(0,0)
            self.hud.touch_up(dict(self.point,TouchPosX=0,TouchPosY=0))
            self.assertEqual(self.owner.preferences.data['position'],saved)

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_owner_move_beats_stale_touch_and_foreign_touch_cannot_steal(self, clock):
        self.start(clock);self.hud.touch_cancel(self.point)
        with patch.object(startup.api,'GetTouchPos',create=True) as touch:
            touch.return_value=(self.point['TouchPosX'],self.point['TouchPosY'])
            self.hud.touch_down(self.point);clock.return_value=10.6
            self.hud.touch_down(dict(self.point,TouchId=2))
            touch.return_value=(0,0);self.hud.drag.update(10.6)
            self.assertIsNone(self.owner.preferences.data['position'])
            moved=dict(self.point,TouchPosX=self.point['TouchPosX']-70)
            self.hud.touch_move(moved)
            saved=list(self.owner.preferences.data['position'])
            self.hud.drag.update(10.7)
            self.hud.touch_cancel(dict(self.point,TouchId=2))
            self.assertIsNotNone(self.hud.drag.press)
            self.assertEqual(self.owner.preferences.data['position'],saved)
            self.hud.touch_cancel(dict(moved,TouchPosX=moved['TouchPosX']-15))
            self.assertIsNone(self.hud.drag.press)
            self.owner.save_preferences.assert_called_once()
            self.owner.open_menu.assert_not_called()

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_capture_target_stays_fixed_and_small_hold_jitter_survives(self, clock):
        self.start(clock)
        target=self.hud.touch_button
        target.SetPosition.reset_mock()
        clock.return_value=10.1
        self.hud.touch_move(dict(self.point,TouchPosX=self.point['TouchPosX']+6))
        self.assertIsNotNone(self.hud.drag.press)
        clock.return_value=10.6
        moved=dict(self.point,TouchPosX=self.point['TouchPosX']-60)
        self.hud.touch_move(moved)
        target.SetPosition.assert_not_called()
        self.hud.touch_up(moved)
        target.SetPosition.assert_called_once_with(self.hud.touch_position)
        self.owner.open_menu.assert_not_called()

    @patch('bongocat_mod.client.hud_drag.time.time')
    def test_invalid_coordinates_and_screen_exit_cannot_move_to_zero(self, clock):
        self.start(clock);clock.return_value=10.6
        self.hud.touch_move(dict(self.point,TouchPosX=self.point['TouchPosX']-40))
        saved=list(self.owner.preferences.data['position'])
        self.hud.touch_move(dict(self.point,TouchPosX=float('nan')))
        self.hud.touch_exit({'TouchPosX':0,'TouchPosY':0})
        self.assertEqual(self.owner.preferences.data['position'],saved)
        self.assertIsNone(self.hud.drag.press)
        self.owner.save_preferences.assert_called_once()


if __name__=='__main__':unittest.main()
