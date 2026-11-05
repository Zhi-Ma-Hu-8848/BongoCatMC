# -*- coding: utf-8 -*-
import math
import time
import mod.client.extraClientApi as api
from bongocat_mod.client.data import KEY_ART


class CatHud(api.GetScreenNodeCls()):
    def __init__(self, namespace, name, param):
        super(CatHud,self).__init__(namespace,name,param)
        self.owner = api.GetSystem('bongocatmc','client')
        self.created = False
        self.doll = None
        self.actor = None
        self.model = -1
        self.error = None
        self.last = 0.
        self.head = [2.,2.]
        self.target = [2.,2.]
        self.rotation = None
        self.sent = {}
        self.top = None
        self.size = None
        self.scale = .55
        self.frames = 0
        self.visible = None
        factory = api.GetEngineCompFactory()
        self.component = factory.CreateModel(api.GetLevelId())
        self.rot = factory.CreateRot(api.GetLocalPlayerId())

    def Create(self):
        self.created = True

    def bind(self):
        self.actor = self.GetBaseUIControl('/root/actor')
        if not self.actor:
            return False
        self.GetBaseUIControl('/root').SetTouchEnable(False)
        self.actor.SetTouchEnable(False)
        self.doll = self.actor.asNeteasePaperDoll()
        ok = self.doll.RenderSkeletonModel({'skeleton_model_name':'bongocatmc_default',
             'animation':'','scale':1.2,'render_depth':-50,'init_rot_y':180,'init_rot_x':0,'init_rot_z':0})
        if not ok:
            self.error = 'RenderSkeletonModel failed'
        return True

    def layout(self):
        size = tuple(self.GetBaseUIControl('/root').GetSize())
        if size == self.size:
            return
        self.size = size
        scale = min(1.25,max(.55,min(size[0]/960.,size[1]/540.)))
        self.scale = scale
        self.actor.SetSize((220*scale,180*scale))
        # Leave the hotbar clear; phone attack controls remain usable underneath.
        self.actor.SetPosition((size[0]-230*scale,size[1]-234*scale))
        self.UpdateScreen(True)

    def follow(self, dt):
        rotation = self.rot.GetRot()
        if rotation and self.rotation:
            pitch = rotation[0]-self.rotation[0]
            yaw = (rotation[1]-self.rotation[1]+180.)%360.-180.
            self.target[0] = max(0.,min(4.,self.target[0]+yaw*.07))
            self.target[1] = max(0.,min(4.,self.target[1]-pitch*.07))
        self.rotation = rotation
        decay = math.exp(-dt*3.)
        rate = 1.-math.exp(-dt*22.)
        for i in range(2):
            self.head[i] += (self.target[i]-self.head[i])*rate
            self.target[i] = 2.+(self.target[i]-2.)*decay

    def render_frame(self):
        if not self.created:
            return
        now = time.time()
        if now-self.last < .001:
            return
        if self.last and now-self.last > .75:
            self.owner.inputs.clear()
            self.rotation = None
        dt = min(.1,now-self.last) if self.last else 0.
        self.last = now
        if self.doll is None and not self.bind():
            return
        self.layout()
        top = api.GetTopUI()
        if top != self.top:
            self.owner.inputs.clear()
            self.rotation = None
            self.top = top
        visible = self.owner.enabled and self.owner.gameplay()
        if not visible or self.error:
            if self.visible is not False:
                self.actor.SetVisible(False)
                self.visible = False
            return
        # Native paper dolls create their model during a visible render pass.
        # Never wait for GetModelId before showing this control: that deadlocks
        # on first load and after a menu was opened before model creation.
        if self.visible is not True:
            self.actor.SetVisible(True)
            self.visible = True
        self.follow(dt)
        state = self.owner.inputs.snapshot(now)
        phase = now%4.1
        blink = max(0.,1.-abs(phase-.12)/.12) if phase < .24 else 0.
        vectors = [(round(self.head[0],4),round(self.head[1],4),blink,float(state['key'])),
                   (float(state['left']),float(state['right']),float(KEY_ART[state['art']]),0.),
                   (.72*self.scale,0.,8.*self.scale,0.)]
        native = self.doll.GetModelId()
        if native != self.model:
            self.model = native
            self.sent = {}
        if self.model >= 0:
            for i, vector in enumerate(vectors,1):
                if self.sent.get(i) != vector:
                    if self.component.SetExtraUniformValue(self.model,i,vector):
                        self.sent[i] = vector
        self.frames += 1

    def Update(self):
        if self.created and time.time()-self.last > .08:
            self.render_frame()

    def Destroy(self):
        self.created = False
        self.doll = None
        if self.owner.hud is self:
            self.owner.hud = None

    def debug_state(self):
        return {'model':self.model,'error':self.error,'top':self.top,'visible':self.visible,
                'size':self.size,'uniforms':self.sent,'frames':self.frames,
                'input':self.owner.inputs.snapshot(time.time()),'events':self.owner.inputs.events}
