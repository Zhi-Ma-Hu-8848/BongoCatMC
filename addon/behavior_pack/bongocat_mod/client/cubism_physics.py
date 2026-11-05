# -*- coding: utf-8 -*-
"""Small client-side Cubism pendulum evaluator for the supplied physics3 rig.

Algorithm adapted from Live2D Cubism Framework (see tools/vendor/framework/LICENSE.md).
No native library, image animation frames, network requests or per-vertex Python work.
"""
import math

def angle(a,b):
    v = math.atan2(b[1],b[0])-math.atan2(a[1],a[0])
    while v < -math.pi: v += 2.*math.pi
    while v > math.pi: v -= 2.*math.pi
    return v

def unit(v):
    length = math.hypot(v[0],v[1])
    return [v[0]/length,v[1]/length] if length > 1e-12 else [0.,1.]

class Physics(object):
    def __init__(self, specification, parameters):
        self.bounds = dict((p['id'],(p['min'],p['max'])) for p in parameters)
        self.bounds['ParamBodyAngleZ'] = (-10.,10.)
        self.spec = specification
        self.step = 1./float(specification['Meta'].get('Fps',120))
        self.reset()

    def reset(self):
        self.remain = 0.
        self.inputs = None
        self.rigs = []
        for spec in self.spec['PhysicsSettings']:
            particles = []; y = 0.
            for i,v in enumerate(spec['Vertices']):
                if i: y += v['Radius']
                particles.append({'p':[0.,y],'v':[0.,0.],'g':[0.,1.],'spec':v})
            self.rigs.append({'spec':spec,'particles':particles,'previous':[0.]*len(spec['Output']),'current':[0.]*len(spec['Output'])})

    def normalized(self, value, ident, spec, reflected):
        lo,hi = self.bounds[ident]
        value = max(lo,min(hi,value));middle = (lo+hi)*.5
        if value > middle:
            result = (value-middle)*(spec['Maximum']-spec['Default'])/(hi-middle)+spec['Default']
        elif value < middle:
            result = (value-middle)*(spec['Minimum']-spec['Default'])/(lo-middle)+spec['Default']
        else: result = spec['Default']
        return result if reflected else -result

    def simulate(self, rig, values):
        spec = rig['spec'];particles = rig['particles'];tx = ty = degrees = 0.
        for entry in spec['Input']:
            ident = entry['Source']['Id'];kind = entry['Type']
            norm = spec['Normalization']['Angle' if kind=='Angle' else 'Position']
            value = self.normalized(values.get(ident,0.),ident,norm,entry['Reflect'])*entry['Weight']*.01
            if kind=='X':tx += value
            elif kind=='Y':ty += value
            else:degrees += value
        rad = math.radians(-degrees);cs = math.cos(rad);sn = math.sin(rad)
        # Preserve Framework's update order for compatibility with authored rigs.
        tx = tx*cs-ty*sn;ty = tx*sn+ty*cs
        particles[0]['p'] = [tx,ty]
        gravity = [math.sin(math.radians(degrees)),math.cos(math.radians(degrees))]
        for i in range(1,len(particles)):
            particle = particles[i];v = particle['spec'];parent = particles[i-1]['p'];old = particle['p'][:]
            delay = v['Delay']*self.step*30.
            dx,dy = old[0]-parent[0],old[1]-parent[1]
            rotation = angle(particle['g'],gravity)/5.;cs = math.cos(rotation);sn = math.sin(rotation)
            dx = cs*dx-dy*sn;dy = sn*dx+dy*cs
            delta = [dx+particle['v'][0]*delay+gravity[0]*v['Acceleration']*delay*delay,
                     dy+particle['v'][1]*delay+gravity[1]*v['Acceleration']*delay*delay]
            direction = unit(delta)
            point = [parent[0]+direction[0]*v['Radius'],parent[1]+direction[1]*v['Radius']]
            if abs(point[0]) < .001*spec['Normalization']['Position']['Maximum']:point[0] = 0.
            if delay:
                particle['v'] = [(point[j]-old[j])/delay*v['Mobility'] for j in (0,1)]
            particle['p'] = point;particle['g'] = gravity[:]
        rig['previous'] = rig['current'][:]
        for j,entry in enumerate(spec['Output']):
            i = entry['VertexIndex'];a = particles[i-1]['p'];b = particles[i]['p'];delta = [b[0]-a[0],b[1]-a[1]]
            if entry['Type']=='Angle':
                parent = [a[k]-particles[i-2]['p'][k] for k in (0,1)] if i>=2 else [0.,1.]
                output = angle(parent,delta)
            else: output = delta[0 if entry['Type']=='X' else 1]
            if entry['Reflect']:output = -output
            rig['current'][j] = output
            self.apply_output(values,entry,output)

    def apply_output(self, values, entry, output):
        ident = entry['Destination']['Id'];lo,hi = self.bounds[ident]
        output = max(lo,min(hi,output*entry['Scale']));weight = entry['Weight']*.01
        values[ident] = values.get(ident,0.)*(1.-weight)+output*weight

    def evaluate(self, values, dt):
        if dt <= 0.:return
        if self.inputs is None:self.inputs = dict(values)
        self.remain += min(.25,dt)
        while self.remain+1e-12 >= self.step:
            weight = min(1.,self.step/self.remain)
            cache = dict((key,self.inputs.get(key,value)*(1.-weight)+value*weight) for key,value in values.items())
            self.inputs = dict(cache)
            for rig in self.rigs:self.simulate(rig,cache)
            self.remain = max(0.,self.remain-self.step)
        fraction = self.remain/self.step
        for rig in self.rigs:
            for i,entry in enumerate(rig['spec']['Output']):
                self.apply_output(values,entry,rig['previous'][i]*(1.-fraction)+rig['current'][i]*fraction)
