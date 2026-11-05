# -*- coding: utf-8 -*-
"""Long-press HUD positioning with mouse/touch coordinates and persistent ratios."""
import time
import mod.client.extraClientApi as api
from bongocat_mod.client.pointer import Pointer


class HudDrag(object):
    HOLD_SECONDS = .45

    def __init__(self, screen):
        self.screen = screen
        self.press = None
        self.motion = None
        self.mouse = False
        self.scale = (1.,1.)
        self.pointer = Pointer(screen,self.cursor)

    def cursor(self):
        if self.motion is None:
            self.motion = api.GetEngineCompFactory().CreateActorMotion(api.GetLocalPlayerId())
        point = self.motion.GetMousePosition() if self.motion is not None else None
        return point if isinstance(point,(tuple,list)) and len(point)==2 else None

    def down(self, args):
        if self.press is not None:
            self.pointer.owns(args)
            return
        if not self.screen.owner.gameplay():
            return
        point = (args.get('TouchPosX'),args.get('TouchPosY'))
        if self.screen.size is None or not self.pointer.begin(args):
            return
        self.mouse,self.scale = self.pointer.mouse,self.pointer.scale
        self.press = {'id':args.get('TouchId',0),'start':point,'point':point,
                      'origin':self.screen.touch_position,'time':time.time(),'dragging':False,
                      'position':None,'canvas':self.screen.size}

    def move(self, args):
        if self.press is None or not self.pointer.record(args):
            return
        self.update(time.time())

    def update(self, now, release=False):
        press = self.press
        if press is None:
            return
        if not self.screen.owner.gameplay() or press['canvas'] != self.screen.size:
            self.cancel()
            return
        value = self.pointer.sample(release)
        if value is not None:press['point'] = value
        delta = tuple(press['point'][i]-press['start'][i] for i in (0,1))
        if not press['dragging']:
            if now-press['time'] < self.HOLD_SECONDS:
                if max(abs(v) for v in delta)>12.*max(1.,self.screen.scale):
                    self.cancel()
                return
            press['dragging'] = True
        if delta == (0.,0.) and press['position'] is None:
            return
        # Keep the touch target on screen, even after a resolution change.
        spans = tuple(max(1.,self.screen.size[i]-self.screen.touch_size[i]-12.) for i in (0,1))
        position = tuple(max(0.,min(1.,(press['origin'][i]+delta[i]-6.)/spans[i])) for i in (0,1))
        if position != press['position']:
            press['position'] = position
            self.screen.owner.preferences.move_position(*position)
            self.screen.layout()

    def up(self, args):
        if self.press is None or not self.pointer.owns(args):
            return
        # Up outside the control may contain (0,0); retain the touch's last
        # move, or poll the real mouse cursor, instead of jumping on release.
        now = time.time()
        if not self.pointer.mouse:self.pointer.record(args,release=True)
        self.update(now,release=True)
        press = self.press
        self.press = None
        self.pointer.end()
        self.screen.touch_button.SetPosition(self.screen.touch_position)
        if press is None:
            return
        if press['dragging']:
            self.screen.owner.save_preferences()
        elif now-press['time'] < self.HOLD_SECONDS:
            self.screen.owner.open_menu()

    def cancel(self, args=None):
        if self.press is None or (args is not None and not self.pointer.owns(args)):
            return
        if args is not None:
            # SDK Cancel is normally release outside the button, not a swipe abort.
            if not self.pointer.mouse:self.pointer.record(args,release=True)
            self.update(time.time(),release=True)
            if self.press is None:return
        dragging = self.press['dragging']
        self.press = None
        self.pointer.end()
        self.screen.touch_button.SetPosition(self.screen.touch_position)
        if dragging:
            self.screen.owner.save_preferences()
