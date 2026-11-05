# -*- coding: utf-8 -*-
import time
import mod.client.extraClientApi as api
from bongocat_mod.client.input_state import InputState, key_art


class CatClient(api.GetClientSystemCls()):
    def __init__(self, namespace, name):
        super(CatClient, self).__init__(namespace, name)
        self.hud = None
        self.ready = False
        self.loaded = False
        self.enabled = True
        self.toggle_held = False
        self.inputs = InputState()
        self.motion = None
        self.sneak_query = None
        self.top = None
        self.bindings = [
            ('UiInitFinished',self.ui_ready), ('OnLocalPlayerStopLoading',self.player_ready),
            ('GameRenderTickEvent',self.render), ('OnKeyPressInGame',self.key),
            ('LeftClickBeforeClientEvent',self.attack_down), ('LeftClickReleaseClientEvent',self.attack_up),
            ('RightClickBeforeClientEvent',self.use_down), ('RightClickReleaseClientEvent',self.use_up),
            ('OnClientPlayerStartMove',self.move_down), ('OnClientPlayerStopMove',self.move_up),
            ('ClientJumpButtonPressDownEvent',self.jump_down), ('ClientJumpButtonReleaseEvent',self.jump_up),
            ('TapBeforeClientEvent',self.tap), ('HoldBeforeClientEvent',self.hold),
            ('TapOrHoldReleaseClientEvent',self.touch_up),
            ('PushScreenEvent',self.menu_change), ('PopScreenEvent',self.menu_change)]
        for event, handler in self.bindings:
            self.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),event,self,handler)

    def ui_ready(self, args):
        if not self.ready:
            api.RegisterUI('bongocatmc','hud','bongocat_mod.client.hud.CatHud','bongocatmc.hud')
        self.ready = True
        self.ensure_hud()

    def player_ready(self, args):
        self.loaded = True
        self.ensure_hud()

    def ensure_hud(self):
        if self.ready and self.loaded and self.hud is None:
            self.hud = api.CreateUI('bongocatmc','hud',{'isHud':1})

    def gameplay(self):
        return api.GetTopUI() in (None, '', 'hud_screen', 'hud')

    def key(self, args):
        code_text = str(args.get('key',''))
        if not code_text.lstrip('-').isdigit():
            return
        code = int(code_text)
        down = str(args.get('isDown')) == '1'
        if code == 119:
            if down and not self.toggle_held and self.gameplay():
                self.enabled = not self.enabled
                self.inputs.clear()
            self.toggle_held = down
            return
        if down and not self.gameplay():
            return
        now = time.time()
        if code in (-99,-98):
            # Key and click events refer to the same physical button.
            self.inputs.click('mouse',0 if code == -99 else 1,down,now)
        else:
            art = key_art(code)
            if art:
                self.inputs.key('key:'+code_text,art,down,now)

    def mouse(self, button, down):
        if not down or self.gameplay():
            self.inputs.click('mouse',button,down,time.time())

    def attack_down(self, args): self.mouse(0,True)
    def attack_up(self, args=None): self.mouse(0,False)
    def use_down(self, args): self.mouse(1,True)
    def use_up(self, args=None): self.mouse(1,False)

    def virtual_key(self, source, art, down):
        if not down or self.gameplay():
            self.inputs.key(source,art,down,time.time())

    def update_movement(self):
        if not self.loaded:
            return
        now = time.time()
        if not self.enabled or not self.gameplay():
            self.inputs.movement(None,now)
            return
        if self.motion is None:
            self.motion = api.GetEngineCompFactory().CreateActorMotion(api.GetLocalPlayerId())
        self.inputs.movement(self.motion.GetInputVector(),now)

    def move_down(self, args=None): self.update_movement()
    def move_up(self, args=None): self.inputs.movement(None,time.time())
    def jump_down(self, args): self.virtual_key('jump','Space',True)
    def jump_up(self, args=None): self.virtual_key('jump','Space',False)

    def update_sneak(self):
        if not self.loaded:
            return
        down = False
        if self.enabled and self.gameplay():
            if self.sneak_query is None:
                self.sneak_query = api.GetEngineCompFactory().CreateQueryVariable(api.GetLocalPlayerId())
            # Touch crouch can toggle rather than hold. Follow the player's
            # actual stance, not generic touch-up, which would release too soon.
            down = bool(self.sneak_query.GetMolangValue('query.is_sneaking'))
        if down != ('sneak' in self.inputs.keys):
            self.inputs.key('sneak','Shift',down,time.time())

    def tap(self, args):
        if self.gameplay():
            self.inputs.click('tap',1,True,time.time())
            self.inputs.click('tap',1,False,time.time())

    def hold(self, args):
        if self.gameplay():
            self.inputs.click('touch',0,True,time.time())

    def touch_up(self, args=None):
        # Mobile/F11 native use buttons press through RightClickBefore, but
        # may release only through TapOrHoldRelease (as in zhima's input fix).
        # Release only the matching native source, keeping other inputs held.
        if 'mouse' in self.inputs.mouse[1]:
            self.use_up(args)
        self.inputs.click('touch',0,False,time.time())
    def menu_change(self, args): self.inputs.clear()

    def render(self, args):
        self.update_movement()
        self.update_sneak()
        if self.hud is not None:
            self.hud.render_frame()

    def Destroy(self):
        for event, handler in self.bindings:
            self.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),event,self,handler)
        self.inputs.clear()
        self.hud = None
