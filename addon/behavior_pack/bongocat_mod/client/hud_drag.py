# -*- coding: utf-8 -*-
"""Long-press HUD positioning with mouse/touch coordinates and persistent ratios."""
import time
import mod.client.extraClientApi as api


class HudDrag(object):
    HOLD_SECONDS = .45

    def __init__(self, screen):
        self.screen = screen
        self.press = None
        self.motion = None
        self.mouse = False
        self.scale = (1.,1.)

    def cursor(self):
        if self.motion is None:
            self.motion = api.GetEngineCompFactory().CreateActorMotion(api.GetLocalPlayerId())
        point = self.motion.GetMousePosition() if self.motion is not None else None
        return point if isinstance(point,(tuple,list)) and len(point)==2 else None

    def down(self, args):
        if self.press is not None or not self.screen.owner.gameplay():
            return
        point = (args.get('TouchPosX'),args.get('TouchPosY'))
        if None in point or self.screen.size is None:
            return
        native = self.cursor()
        self.mouse = native is not None
        self.scale = (1.,1.)
        if native is not None:
            pixels = api.GetEngineCompFactory().CreateGame(api.GetLevelId()).GetScreenSize()
            if isinstance(pixels,(tuple,list)) and min(pixels)>0:
                scale = tuple(self.screen.size[i]/float(pixels[i]) for i in (0,1))
                if sum((native[i]*scale[i]-point[i])**2 for i in (0,1)) < sum((native[i]-point[i])**2 for i in (0,1)):
                    self.scale = scale
        self.press = {'id':args.get('TouchId',0),'start':point,'point':point,
                      'origin':self.screen.touch_position,'time':time.time(),'dragging':False,
                      'position':None,'canvas':self.screen.size}

    def move(self, args):
        if self.press is None or args.get('TouchId',0)!=self.press['id']:
            return
        point = (args.get('TouchPosX'),args.get('TouchPosY'))
        if not self.mouse and None not in point:
            self.press['point'] = point
        self.update(time.time())

    def update(self, now):
        press = self.press
        if press is None:
            return
        if not self.screen.owner.gameplay() or press['canvas'] != self.screen.size:
            self.cancel()
            return
        if self.mouse:
            point = self.cursor()
            if point is not None:
                press['point'] = tuple(point[i]*self.scale[i] for i in (0,1))
        delta = tuple(press['point'][i]-press['start'][i] for i in (0,1))
        if not press['dragging']:
            if now-press['time'] < self.HOLD_SECONDS:
                if max(abs(v) for v in delta)>8.*self.screen.scale:
                    self.press = None
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
        if self.press is None or args.get('TouchId',0)!=self.press['id']:
            return
        # Up outside the control may contain (0,0); retain the touch's last
        # move, or poll the real mouse cursor, instead of jumping on release.
        now = time.time()
        self.update(now)
        press = self.press
        self.press = None
        if press is None:
            return
        if press['dragging']:
            self.screen.owner.save_preferences()
        elif now-press['time'] < self.HOLD_SECONDS:
            self.screen.owner.open_menu()

    def cancel(self, args=None):
        if self.press is None or (args is not None and args.get('TouchId',self.press['id'])!=self.press['id']):
            return
        dragging = self.press['dragging']
        self.press = None
        if dragging:
            self.screen.owner.save_preferences()
