# -*- coding: utf-8 -*-
"""Original Cubism parameter timelines, independent of rendering frame rate."""
import math
from bongocat_mod.client.motion_data import MOTIONS


def cubic(a, b, c, d, t):
    s = 1.-t
    return s*s*s*a+3*s*s*t*b+3*s*t*t*c+t*t*t*d


def curve_value(segments, clock):
    x, y = segments[:2]
    i = 2
    while i < len(segments):
        kind = segments[i]
        size = 6 if kind == 1 else 2
        points = segments[i+1:i+1+size]
        end_x, end_y = points[-2:]
        if clock <= end_x:
            if clock <= x:
                return y
            if kind == 2:
                return y if clock < end_x else end_y
            if kind == 3:
                return end_y
            if kind == 0:
                return y+(end_y-y)*(clock-x)/max(1e-9,end_x-x)
            # Unrestricted Cubism Beziers need inversion of the time axis.
            lo, hi = 0., 1.
            for unused in range(20):
                t = (lo+hi)*.5
                if cubic(x,points[0],points[2],end_x,t) < clock:
                    lo = t
                else:
                    hi = t
            return cubic(y,points[1],points[3],end_y,(lo+hi)*.5)
        x, y = end_x, end_y
        i += size+1
    return y


class Effects(object):
    def __init__(self):
        self.expression = 'default'
        self.start_values = [0.,0.]
        self.target = [0.,0.]
        self.changed = 0.
        self.fade = [.8,.5]
        self.motion = None
        self.started = 0.

    def expression_values(self, now):
        values = []
        for i in range(2):
            elapsed = max(0.,min(1.,(now-self.changed)/self.fade[i]))
            weight = .5-.5*math.cos(math.pi*elapsed)
            values.append(self.start_values[i]+(self.target[i]-self.start_values[i])*weight)
        return values

    def select(self, name, now):
        if name not in ('default','glasses','halo'):
            return
        self.start_values = self.expression_values(now)
        self.expression = 'default' if name == self.expression else name
        self.target = [float(self.expression=='glasses'),float(self.expression=='halo')]
        self.fade = [.8 if self.target[0] else 1., .5 if self.target[1] else 1.]
        self.changed = now

    def play(self, name, now):
        if name in MOTIONS:
            self.motion, self.started = name, now

    def clear(self, now):
        self.start_values = self.expression_values(now)
        self.expression = None
        self.target = [0.,0.]
        self.fade = [1.,1.]
        self.changed = now

    def stop(self):
        self.motion = None

    def sample(self, now):
        values = {'Param':0.,'Param2':0.,'Param3':0.}
        if self.motion:
            motion = MOTIONS[self.motion]
            clock = max(0.,now-self.started)
            if clock >= motion['Meta']['Duration']:
                self.stop()
            else:
                for curve in motion['Curves']:
                    values[curve['Id']] = curve_value(curve['Segments'],clock)
        expression = self.expression_values(now)
        return (expression[0],expression[1],values['Param3'],values['Param2']), values['Param']


class TapGesture(object):
    def __init__(self):
        self.touch = None

    def down(self, args, now):
        self.touch = (args.get('TouchId',0),args.get('TouchPosX',0),args.get('TouchPosY',0),now)

    def move(self, args, scale):
        if self.touch and args.get('TouchId',0) == self.touch[0]:
            dx = args.get('TouchPosX',self.touch[1])-self.touch[1]
            dy = args.get('TouchPosY',self.touch[2])-self.touch[2]
            if dx*dx+dy*dy > (10*scale)**2:
                self.touch = None

    def up(self, args, now, scale):
        self.move(args,scale)
        valid = self.touch is not None and args.get('TouchId',0)==self.touch[0] and now-self.touch[3]<.65
        self.touch = None
        return valid

    def cancel(self):
        self.touch = None
