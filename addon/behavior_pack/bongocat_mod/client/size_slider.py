# -*- coding: utf-8 -*-
"""Coordinate-driven slider, matching the reference mod's color picker."""
import math
import mod.client.extraClientApi as api
from bongocat_mod.client.pointer import Pointer


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
        self.pointer = Pointer(screen,self.mouse_position)

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
        button.SetButtonScreenExitCallback(self.exit)
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
        if self.touch is not None:
            self.pointer.owns(args)
            return
        if self.screen.expanded != 'settings' or not self.pointer.begin(args):
            return
        self.touch = self.pointer.ident
        self.mouse,self.mouse_scale = self.pointer.mouse,self.pointer.scale
        self.sample(self.pointer.value[0])

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
        if self.touch is not None and self.pointer.record(args):
            self.poll()

    def poll(self, release=False):
        if self.touch is None:
            return
        point = self.pointer.sample(release)
        if point is not None:self.sample(point[0])

    def up(self, args):
        if self.touch is None or not self.pointer.owns(args):
            return
        if not self.pointer.mouse:self.pointer.record(args,release=True)
        self.poll(release=True)
        self.finish()

    def cancel(self, args):
        self.up(args)

    def exit(self, args):
        self.finish()

    def finish(self):
        if self.touch is not None:
            self.touch = None
            self.pointer.end()
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
