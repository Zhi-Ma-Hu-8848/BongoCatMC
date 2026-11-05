# -*- coding: utf-8 -*-
"""Captured pointer, based on Balatro pointer_input and zhima preview input."""
import math
import mod.client.extraClientApi as api


def point(value):
    if not isinstance(value,(tuple,list)) or len(value)!=2:
        return None
    if not all(isinstance(v,(int,float)) and not math.isnan(v) and not math.isinf(v) for v in value):
        return None
    return tuple(value)


class Pointer(object):
    def __init__(self, screen, mouse):
        self.screen,self.get_mouse = screen,mouse
        self.active = False

    def touch_position(self):
        getter = getattr(api,'GetTouchPos',None)
        return point(getter()) if getter else None

    def begin(self, args):
        origin = point((args.get('TouchPosX'),args.get('TouchPosY')))
        if origin is None:return False
        self.active=True;self.ident=args.get('TouchId',0);self.value=origin
        self.foreign=False;self.callback=False;self.pending=False
        native=point(self.get_mouse());self.mouse=native is not None
        if native is None:native=self.touch_position()
        self.native=native;self.scale=(1.,1.);self.poll_touch=False
        if native is not None:
            size=point(self.screen.GetBaseUIControl('/root').GetSize())
            pixels=point(api.GetEngineCompFactory().CreateGame(api.GetLevelId()).GetScreenSize())
            if size and pixels and min(pixels)>0:
                scale=tuple(size[i]/float(pixels[i]) for i in (0,1))
                direct=sum((native[i]-origin[i])**2 for i in (0,1))
                scaled=sum((native[i]*scale[i]-origin[i])**2 for i in (0,1))
                if scaled<direct:self.scale=scale
                self.poll_touch=not self.mouse and min(direct,scaled)<=49.
        return True

    def owns(self, args):
        if not self.active:return False
        if args.get('TouchId',0)!=self.ident:
            self.foreign=True
            return False
        return True

    def record(self, args, release=False):
        if not self.owns(args):return False
        value=point((args.get('TouchPosX'),args.get('TouchPosY')))
        # Outside releases can contain a dummy zero coordinate. Never poll an
        # unowned global touch at release: it may already describe another finger.
        if value is not None and (not (release or self.mouse) or value!=(0.,0.)):
            self.value=value;self.callback=True;self.pending=True
        return True

    def sample(self, release=False):
        if not self.active:return None
        if self.pending:
            self.pending=False
            return self.value
        if self.mouse:
            native=point(self.get_mouse())
            # A stale PC cursor must not undo a valid simulated-touch callback.
            if native is not None and (not self.callback or native!=self.native):
                self.native=native
                self.value=tuple(native[i]*self.scale[i] for i in (0,1))
        elif not release and not self.callback and self.poll_touch and not self.foreign:
            native=self.touch_position()
            if native is not None and native!=self.native:
                self.native=native
                self.value=tuple(native[i]*self.scale[i] for i in (0,1))
        return self.value

    def end(self):
        self.active=False
