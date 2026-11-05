# -*- coding: utf-8 -*-
"""Client-only appearance settings with bounded, persistent values."""
import math

MIRROR_KEYS = ('flip_vertical','flip_horizontal')
TOGGLE_KEYS = MIRROR_KEYS+('mouse_recenter',)

class Preferences(object):
    def __init__(self, data=None):
        self.data = {'size':1.,'flip_vertical':False,'flip_horizontal':False,'mouse_recenter':False,'position':None,'model':'default'}
        if isinstance(data,dict):
            if data.get('model') in ('default','deepseek'):
                self.data['model'] = data['model']
            for key, lo, hi in [('size',.5,2.)]:
                value = data.get(key)
                if isinstance(value,(int,float)) and not math.isnan(value) and not math.isinf(value):
                    self.data[key] = max(lo,min(hi,float(value)))
            for key in TOGGLE_KEYS:
                if isinstance(data.get(key),bool):
                    self.data[key] = data[key]
            position = data.get('position')
            if isinstance(position,(list,tuple)) and len(position)==2 and all(
                    isinstance(v,(int,float)) and not math.isnan(v) and not math.isinf(v) for v in position):
                self.data['position'] = [max(0.,min(1.,float(v))) for v in position]
        self.dirty = False

    def ratio(self, key):
        return (self.data[key]-.5)/1.5

    def change(self, key, ratio):
        if key != 'size' or not isinstance(ratio,(int,float)) or math.isnan(ratio) or math.isinf(ratio):
            return False
        ratio = max(0.,min(1.,float(ratio)))
        value = round(.5+ratio*1.5,3)
        if value == self.data[key]:
            return False
        self.data[key] = value
        self.dirty = True
        return True

    def toggle(self, key):
        if key not in TOGGLE_KEYS:
            return False
        self.data[key] = not self.data[key]
        self.dirty = True
        return True

    def move_position(self, x, y):
        position = [round(max(0.,min(1.,v)),6) for v in (x,y)]
        if position == self.data['position']:
            return
        self.data['position'] = position
        self.dirty = True
