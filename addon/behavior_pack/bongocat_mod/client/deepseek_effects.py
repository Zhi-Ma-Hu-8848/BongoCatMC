# -*- coding: utf-8 -*-
"""Original parameter curves, breathing, blink, expressions and live physics."""
import math
import random
from collections import OrderedDict
from bongocat_mod.client.deepseek_parameters import PARAMETERS, PHYSICS, EXPRESSIONS, MOTIONS, KEY_ART
from bongocat_mod.client.effects import curve_value
from bongocat_mod.client.cubism_physics import Physics

DEFAULTS = dict((p['id'],p['default']) for p in PARAMETERS)

def smooth(value):
    return .5-.5*math.cos(math.pi*max(0.,min(1.,value)))

def persistent(clip):
    enables = False
    for curve in clip['Curves']:
        if curve['Target'] != 'Parameter':continue
        values = curve['Segments'];normal = DEFAULTS.get(curve['Id'],0.)
        if abs(values[1]-normal)<.0001 and abs(values[-1]-normal)<.0001:
            cursor = 2
            while cursor<len(values):
                size = 6 if values[cursor]==1 else 2
                if any(abs(v-normal)>.0001 for v in values[cursor+2:cursor+size+1:2]):return False
                cursor += size+1
        enables = enables or abs(values[-1]-normal)>.0001
    return enables

class DeepseekEffects(object):
    def __init__(self):
        self.expression = None
        self.expression_from = dict((name,0.) for name in EXPRESSIONS)
        self.expression_to = dict(self.expression_from)
        self.changed = 0.
        self.runs = OrderedDict()
        self.motion = None
        self.started = 0.
        self.last = None
        self.clock = 0.
        self.face = [0.,0.]
        self.velocity = [0.,0.]
        self.physics = Physics(PHYSICS,PARAMETERS)
        self.random = random.Random()
        self.blink_state = 'interval'
        self.blink_at = 0.
        self.blink_next = self.random.random()*7.
        self.parameters = dict(DEFAULTS)
        self.overlay = False

    def expression_weights(self, now):
        result = {}
        for name,entry in EXPRESSIONS.items():
            target = self.expression_to[name]
            duration = entry.get('FadeInTime' if target else 'FadeOutTime',1.)
            weight = smooth((now-self.changed)/duration) if duration>0 else 1.
            result[name] = self.expression_from[name]+(target-self.expression_from[name])*weight
        return result

    def expression_weight(self, now):
        return max(self.expression_weights(now).values())

    def select(self, name, now):
        if name not in EXPRESSIONS:return
        if name == self.expression:
            self.clear(now);return
        self.expression_from = self.expression_weights(now)
        self.expression = name
        self.expression_to = dict((key,float(key==name)) for key in EXPRESSIONS)
        self.changed = now

    def clear(self, now):
        self.expression_from = self.expression_weights(now)
        self.expression_to = dict((key,0.) for key in EXPRESSIONS)
        self.expression = None
        self.changed = now

    def is_selected(self, name):
        return name in self.runs

    def play(self, name, now):
        if name not in MOTIONS:return False
        if name in self.runs and persistent(MOTIONS[name]):
            del self.runs[name]
            self.motion = list(self.runs)[-1] if self.runs else None
            return False
        # Only replace runs controlling the same set of authored parameters.
        signature = set(c['Id'] for c in MOTIONS[name]['Curves'])
        for previous in list(self.runs):
            if set(c['Id'] for c in MOTIONS[previous]['Curves'])==signature:del self.runs[previous]
        self.runs[name] = now
        self.motion = name
        self.started = now
        return True

    def stop(self):
        self.runs.clear()
        self.motion = None

    def motion_values(self, now):
        values = {}
        playing = False
        for name,started in list(self.runs.items()):
            clip = MOTIONS[name];duration = clip['Meta']['Duration'];clock = max(0.,now-started)
            if clock>=duration and not persistent(clip):
                del self.runs[name];continue
            playing = playing or clock<duration
            # The desktop classifies these as one-shot or persistent states,
            # regardless of the editor's legacy Loop flag.
            for curve in clip['Curves']:
                if curve['Target']=='Parameter':values[curve['Id']] = curve_value(curve['Segments'],min(clock,duration))
        self.motion = list(self.runs)[-1] if self.runs else None
        return values,playing

    def sample(self, now):
        # Compatibility with the common menu/HUD lifecycle; frame() does render work.
        self.motion_values(now)
        return (0.,0.,0.,0.),0.

    def blink(self, dt, motion_playing):
        # Cubism's blink updater yields while a motion updates parameters.
        if motion_playing:return 1.
        self.blink_at += dt
        if self.blink_state=='interval':
            if self.blink_at>=self.blink_next:self.blink_state='closing';self.blink_at=0.
            return 1.
        if self.blink_state=='closing':
            value = max(0.,1.-self.blink_at/.1)
            if self.blink_at>=.1:self.blink_state='closed';self.blink_at=0.
            return value
        if self.blink_state=='closed':
            if self.blink_at>=.05:self.blink_state='opening';self.blink_at=0.
            return 0.
        value = min(1.,self.blink_at/.15)
        if self.blink_at>=.15:
            self.blink_state='interval';self.blink_at=0.;self.blink_next=self.random.random()*7.
        return value

    def look(self, target, dt):
        # Acceleration/deceleration rather than a second exponential follower.
        distance = [max(-1.,min(1.,target[i]))-self.face[i] for i in (0,1)]
        length = math.hypot(*distance)
        if length<.001:
            self.face = list(target);self.velocity = [0.,0.];return
        acceleration = 7.2727275/.15
        speed = min(7.2727275,math.sqrt(2.*acceleration*length))
        desired = [v/length*speed for v in distance]
        delta = [desired[i]-self.velocity[i] for i in (0,1)]
        change = math.hypot(*delta);factor = min(1.,acceleration*dt/max(change,1e-9))
        self.velocity = [self.velocity[i]+delta[i]*factor for i in (0,1)]
        step = [v*dt for v in self.velocity]
        if math.hypot(*step)>length:self.face=list(target);self.velocity=[0.,0.]
        else:self.face=[self.face[i]+step[i] for i in (0,1)]

    def frame(self, now, target, state):
        elapsed = now-self.last if self.last is not None else 1./60.
        if elapsed>.75:
            self.physics.reset();self.velocity=[0.,0.]
        dt = max(0.,min(.1,elapsed));self.last=now;self.clock+=dt
        self.look(target,dt)
        values = dict(DEFAULTS);motion,playing = self.motion_values(now);values.update(motion)
        eye = self.blink(dt,playing);values['ParamEyeLOpen']=eye;values['ParamEyeROpen']=eye
        x,y = self.face
        values['ParamAngleX'] += x*54.
        values['ParamAngleY'] += y*36.
        values['ParamAngleZ'] += -x*y*30.
        values['ParamBodyAngleX'] += x*12.
        for ident,offset,peak,period in [('ParamAngleX',0.,15.,6.5345),('ParamAngleY',0.,8.,3.5345),
                ('ParamAngleZ',0.,10.,5.5345),('ParamBodyAngleX',0.,4.,15.5345),('ParamBreath',.5,.5,3.2345)]:
            values[ident] += (offset+peak*math.sin(2.*math.pi*self.clock/period))*.5
        for name,weight in self.expression_weights(now).items():
            for entry in EXPRESSIONS[name]['Parameters']:
                ident=entry['Id'];value=entry['Value'];blend=entry.get('Blend','Add')
                if blend=='Multiply':values[ident]*=1.+(value-1.)*weight
                elif blend=='Overwrite':values[ident]=values[ident]*(1.-weight)+value*weight
                else:values[ident]+=value*weight
        values['ParamMouseX'] = target[0]*30.
        values['ParamMouseY'] = target[1]*30.
        values['ParamMouseLeftDown'] = float(state['left'])
        values['ParamMouseRightDown'] = float(state['right'])
        self.overlay = bool(state['key'] and state['art'] in KEY_ART and values.get('Hellovisible',0.)<.01)
        if self.overlay:values['CatParamLeftHandDown']=1.
        for p in PARAMETERS:values[p['id']] = max(p['min'],min(p['max'],values[p['id']]))
        self.physics.evaluate(values,dt)
        self.parameters = values
        return values

    def packed(self, appearance, state):
        channels = []
        for p in PARAMETERS:
            value = max(p['min'],min(p['max'],self.parameters[p['id']]))
            if p['min']==-p['max']:
                encoded = 128+int(round(value/p['max']*127.))
            else:encoded = int(round((value-p['min'])/(p['max']-p['min'])*255.))
            channels.append(encoded)
        channels.extend([KEY_ART.get(state['art'],KEY_ART['KeyW']),255 if self.overlay else 0])
        channels.extend([0]*(36-len(channels)))
        values = [float(channels[i]+256*channels[i+1]+65536*channels[i+2]) for i in range(0,36,3)]
        return [tuple(values[:4]),tuple(values[4:8]),appearance,tuple(values[8:12])]
