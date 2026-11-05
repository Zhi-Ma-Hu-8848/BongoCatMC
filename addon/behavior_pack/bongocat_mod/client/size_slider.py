# -*- coding: utf-8 -*-
"""Coordinate-driven slider, matching the reference mod's color picker."""
import math
import mod.client.extraClientApi as api


class SizeSlider(object):

    def __init__(self, screen):
        self.screen = screen
        self.path = None
        self.content = None
        self.touch = None
        self.motion = None
        self.mouse = False
        self.mouse_scale = (1.,1.)
        self.painted = None

    def bind(self):
        self.content = self.screen.contents['settings']
        self.path = self.content+'/size'
        base = self.screen.GetBaseUIControl(self.path)
        if base is None or base.asButton() is None:
            return False
        button = base.asButton()
        button.AddTouchEventParams({'isSwallow':True})
        button.SetButtonTouchDownCallback(self.down)
        button.SetButtonTouchMoveCallback(self.move)
        button.SetButtonTouchUpCallback(self.up)
        button.SetButtonTouchCancelCallback(self.cancel)
        button.SetButtonScreenExitCallback(self.cancel)
        self.paint()
        return True

    def mouse_position(self):
        if self.motion is None:
            self.motion = api.GetEngineCompFactory().CreateActorMotion(api.GetLocalPlayerId())
        point = self.motion.GetMousePosition() if self.motion is not None else None
        if not isinstance(point,(tuple,list)) or len(point) != 2:
            return None
        return point

    def down(self, args):
        if self.screen.expanded != 'settings' or self.touch is not None:
            return
        point = (args.get('TouchPosX'),args.get('TouchPosY'))
        if None in point:
            return
        self.touch = args.get('TouchId',0)
        self.mouse_scale = (1.,1.)
        native = self.mouse_position()
        self.mouse = native is not None
        if native is not None:
            # As in zhima.skin_preview_input, choose the units that match Down.
            size = self.screen.GetBaseUIControl('/root').GetSize()
            pixels = api.GetEngineCompFactory().CreateGame(api.GetLevelId()).GetScreenSize()
            if isinstance(pixels,(tuple,list)) and min(pixels)>0:
                scale = (size[0]/float(pixels[0]),size[1]/float(pixels[1]))
                if sum((native[i]*scale[i]-point[i])**2 for i in (0,1)) < sum((native[i]-point[i])**2 for i in (0,1)):
                    self.mouse_scale = scale
        self.sample(point[0])

    def sample(self, x):
        if not isinstance(x,(int,float)) or math.isnan(x) or math.isinf(x):
            return
        base = self.screen.GetBaseUIControl(self.path)
        left = base.GetGlobalPosition()[0]
        width = base.GetSize()[0]
        if width <= 14:
            return
        ratio = max(0.,min(1.,(x-left-7.)/(width-14.)))
        self.screen.owner.preferences.change('size',ratio)
        self.paint()

    def move(self, args):
        if self.touch is None or args.get('TouchId',0) != self.touch:
            return
        if self.mouse:
            self.poll()
        else:
            self.sample(args.get('TouchPosX'))

    def poll(self):
        if self.touch is None or not self.mouse:
            return
        point = self.mouse_position()
        if point is not None:
            self.sample(point[0]*self.mouse_scale[0])

    def up(self, args):
        if self.touch is None or args.get('TouchId',0) != self.touch:
            return
        # Mouse Up outside a control can contain (0,0). Read the real cursor;
        # on touch, retain the last Down/Move sample belonging to this finger.
        self.poll()
        self.finish()

    def cancel(self, args):
        if self.touch is not None and args.get('TouchId',self.touch) == self.touch:
            self.finish()

    def finish(self):
        if self.touch is not None:
            self.touch = None
            self.screen.owner.save_preferences()

    def paint(self):
        if self.path is None:
            return
        base = self.screen.GetBaseUIControl(self.path)
        if base is None:
            return
        width = base.GetSize()[0]
        if width <= 14:
            return
        ratio = self.screen.owner.preferences.ratio('size')
        state = (width,ratio)
        if state == self.painted:
            return
        self.painted = state
        offset = ratio*(width-14.)
        self.screen.GetBaseUIControl(self.path+'/thumb').SetPosition((offset,4))
        self.screen.GetBaseUIControl(self.path+'/fill').SetSize((7.+offset,4))
        self.screen.GetBaseUIControl(self.content+'/size_value').asLabel().SetText(
            u'%d%%'%int(self.screen.owner.preferences.data['size']*100+.5))
