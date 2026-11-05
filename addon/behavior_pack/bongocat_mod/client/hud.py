# -*- coding: utf-8 -*-
import math
import time
import mod.client.extraClientApi as api
from bongocat_mod.client.data import KEY_ART
from bongocat_mod.client.hud_drag import HudDrag


class CatHud(api.GetScreenNodeCls()):
    def __init__(self, namespace, name, param):
        super(CatHud,self).__init__(namespace,name,param)
        self.owner = api.GetSystem('bongocatmc','client')
        self.created = False
        self.doll = None
        self.actor = None
        self.model = -1
        self.model_kind = None
        self.error = None
        self.last = 0.
        self.head = [2.,2.]
        self.target = [2.,2.]
        self.rotation = None
        self.sent = {}
        self.top = None
        self.size = None
        self.appearance_size = None
        self.scale = .55
        self.frames = 0
        self.visible = None
        self.touch_button = None
        self.drag = HudDrag(self)
        self.position_key = None
        self.touch_position = (0.,0.)
        self.touch_size = (1.,1.)
        factory = api.GetEngineCompFactory()
        self.component = factory.CreateModel(api.GetLevelId())
        self.rot = factory.CreateRot(api.GetLocalPlayerId())

    def Create(self):
        self.created = True
        self.owner.hud = self

    def bind(self):
        self.actor = self.GetBaseUIControl('/root/actor')
        if not self.actor:
            return False
        self.actor.SetTouchEnable(False)
        self.touch_button = self.GetBaseUIControl('/root/touch').asButton()
        self.touch_button.AddTouchEventParams({'isSwallow':True})
        self.touch_button.SetButtonTouchDownCallback(self.touch_down)
        self.touch_button.SetButtonTouchMoveCallback(self.touch_move)
        self.touch_button.SetButtonTouchUpCallback(self.touch_up)
        self.touch_button.SetButtonTouchCancelCallback(self.touch_cancel)
        self.touch_button.SetButtonScreenExitCallback(self.touch_exit)
        self.doll = self.actor.asNeteasePaperDoll()
        self.apply_model()
        return True

    def apply_model(self):
        kind = self.owner.preferences.data['model']
        if kind == self.model_kind:
            return
        self.model_kind = kind
        self.sent = {}
        self.model = -1
        self.size = None
        self.error = None
        ok = self.doll.RenderSkeletonModel({'skeleton_model_name':'bongocatmc_'+kind,
             'animation':'','scale':1.2,'render_depth':-50,'init_rot_y':180,'init_rot_x':0,'init_rot_z':0})
        if not ok:
            self.error = 'RenderSkeletonModel failed'

    def layout(self):
        size = tuple(self.GetBaseUIControl('/root').GetSize())
        amount = self.owner.preferences.data['size']
        position = self.owner.preferences.data['position']
        position = tuple(position) if position is not None else None
        metrics_changed = size != self.size or amount != self.appearance_size
        if not metrics_changed and position == self.position_key:
            return
        self.position_key = position
        self.size = size
        self.appearance_size = amount
        scale = min(1.25,max(.55,min(size[0]/960.,size[1]/540.)))
        self.scale = scale
        if metrics_changed:
            self.actor.SetSize((220*scale,180*scale))
        # Leave the hotbar clear; phone attack controls remain usable underneath.
        # Narrow target over the cat, leaving the native mobile use control free.
        deepseek = self.owner.preferences.data['model'] == 'deepseek'
        self.touch_size = (110*scale*amount,(115 if deepseek else 64)*scale*amount)
        original = (size[0]-10*scale-168*scale*amount,size[1]-92*scale-(144 if deepseek else 93)*scale*amount)
        self.touch_position = original if position is None else tuple(
            6.+position[i]*max(1.,size[i]-self.touch_size[i]-12.) for i in (0,1))
        shift = tuple(self.touch_position[i]-original[i] for i in (0,1))
        self.actor.SetPosition((size[0]-230*scale+shift[0],size[1]-234*scale+shift[1]))
        if metrics_changed:
            self.touch_button.SetSize(self.touch_size)
        # Keep the original native capture target still while the artwork moves.
        # Up/Cancel places the target at the final location after ending capture.
        if not self.drag.press:self.touch_button.SetPosition(self.touch_position)
        if metrics_changed:
            self.UpdateScreen(True)

    def touch_down(self, args):
        self.drag.down(args)

    def touch_move(self, args):
        self.drag.move(args)

    def touch_up(self, args):
        self.drag.up(args)

    def touch_cancel(self, args):
        self.drag.cancel(args)

    def touch_exit(self, args):
        self.drag.cancel()

    def follow(self, dt):
        deepseek = self.owner.preferences.data['model'] == 'deepseek'
        if self.owner.menu is self:
            point = self.drag.cursor()
            if point is not None:
                pixels = api.GetEngineCompFactory().CreateGame(api.GetLevelId()).GetScreenSize()
                if isinstance(pixels,(tuple,list)) and min(pixels)>0:
                    self.target = [max(0.,min(4.,point[0]/float(pixels[0])*4.)),
                                   max(0.,min(4.,4.-point[1]/float(pixels[1])*4.))]
                    # Share menu pointer input across models, while retaining
                    # the default cat's smoothing and DeepSeek's own look solver.
                    rate = 1. if deepseek else 1.-math.exp(-dt*22.)
                    for i in range(2):
                        self.head[i] += (self.target[i]-self.head[i])*rate
                    self.rotation = None
                    return
        rotation = self.rot.GetRot()
        if rotation and self.rotation:
            pitch = rotation[0]-self.rotation[0]
            yaw = (rotation[1]-self.rotation[1]+180.)%360.-180.
            self.target[0] = max(0.,min(4.,self.target[0]+yaw*.07))
            self.target[1] = max(0.,min(4.,self.target[1]-pitch*.07))
        self.rotation = rotation
        decay = math.exp(-dt*3.) if self.owner.preferences.data['mouse_recenter'] else 1.
        rate = 1.-math.exp(-dt*22.)
        for i in range(2):
            if deepseek:self.head[i] = self.target[i]
            else:self.head[i] += (self.target[i]-self.head[i])*rate
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
            self.drag.cancel()
        dt = min(.1,now-self.last) if self.last else 0.
        self.last = now
        if self.doll is None and not self.bind():
            return
        self.apply_model()
        self.layout()
        self.drag.update(now)
        top = api.GetTopUI()
        if top != self.top:
            self.owner.inputs.clear()
            self.rotation = None
            self.top = top
        visible = self.owner.enabled and (self.owner.gameplay() or self.owner.menu is self)
        self.touch_button.SetVisible(visible and self.owner.gameplay())
        effects, flash = self.owner.effects.sample(now)
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
        deepseek = self.model_kind == 'deepseek'
        key = float(state['key']) if self.owner.effects.motion != 'wave' else 0.
        art = KEY_ART.get(state['art'],KEY_ART['KeyW'])
        phase = now%4.1
        blink = max(0.,1.-abs(phase-.12)/.12) if phase < .24 else 0.
        amount = self.owner.preferences.data['size']
        zoom = .72*self.scale
        # Grow up and left from the existing bottom-right canvas corner.
        mirror = int(self.owner.preferences.data['flip_horizontal'])+2*int(self.owner.preferences.data['flip_vertical'])
        appearance = (zoom*amount,24.*zoom*(306./354.)*(1.-amount),
                      8.*self.scale+12.*zoom*(amount-1.),float(mirror))
        vectors = [(round(self.head[0],4),round(self.head[1],4),blink,key),
                   (float(state['left']),float(state['right']),float(art),flash),
                   appearance,effects]
        if deepseek:
            self.owner.effects.frame(now,[(v-2.)*.5 for v in self.head],state)
            vectors = self.owner.effects.packed(appearance,state)
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
        self.drag.cancel()
        self.created = False
        self.doll = None
        if self.owner.hud is self:
            self.owner.hud = None

    def debug_state(self):
        return {'model':self.model,'error':self.error,'top':self.top,'visible':self.visible,
                'size':self.size,'uniforms':self.sent,'frames':self.frames,
                'input':self.owner.inputs.snapshot(time.time()),'events':self.owner.inputs.events}
