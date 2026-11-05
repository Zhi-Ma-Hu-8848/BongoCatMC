# -*- coding: utf-8 -*-
import time
import mod.client.extraClientApi as api
from bongocat_mod.client.hud import CatHud
from bongocat_mod.client.effects import TapGesture
from bongocat_mod.client.menu_catalog import ENTRIES, LIST_WIDTH, ROW_HEIGHT, MAX_VISIBLE_ROWS, entries_for
from bongocat_mod.client.size_slider import SizeSlider
from bongocat_mod.client.preferences import TOGGLE_KEYS


class CatMenu(CatHud):
    def __init__(self, namespace, name, param):
        super(CatMenu,self).__init__(namespace,name,param)
        self.callbacks = []
        self.bound = False
        self.state = None
        self.expanded = None
        self.contents = {}
        self.row_gesture = TapGesture()
        self.pressed_row = None
        self.size_slider = SizeSlider(self)

    def Create(self):
        self.created = True
        self.owner.menu = self
        self.bind_buttons()

    def scroll(self, group):
        return self.GetBaseUIControl('/'+group+'/list').asScrollView()

    def bind_buttons(self):
        if self.bound or not self.GetBaseUIControl('/close'):
            return
        for group in list(ENTRIES)+['settings']:
            path = self.scroll(group).GetScrollViewContentPath()
            if not path:
                return
            self.contents[group] = path if path.startswith('/') else '/'+path
        for name in ('close','settings','motions','expressions','models','outside'):
            callback = self.toolbar_action(name)
            self.callbacks.append(callback)
            path = '/'+name if name in ('close','outside') else '/bar/'+name
            button = self.GetBaseUIControl(path).asButton()
            button.AddTouchEventParams({'isSwallow':True})
            button.SetButtonTouchUpCallback(callback)
        settings_entries = tuple((key,None) for key in TOGGLE_KEYS)
        for group, entries in list(ENTRIES.items())+[('settings',settings_entries)]:
            for key, unused in entries:
                button = self.GetBaseUIControl(self.contents[group]+'/item_'+key).asButton()
                button.AddTouchEventParams({'isSwallow':False})
                for setter,phase in [(button.SetButtonTouchDownCallback,'down'),(button.SetButtonTouchMoveCallback,'move'),
                                     (button.SetButtonTouchUpCallback,'up'),(button.SetButtonTouchCancelCallback,'cancel')]:
                    callback = self.row_callback(group,key,phase)
                    self.callbacks.append(callback)
                    setter(callback)
        if not self.size_slider.bind():
            return
        self.bound = True
        self.refresh()

    def toolbar_action(self, name):
        def callback(args):
            # The transparent backdrop only absorbs input; it is not Back.
            if name == 'outside':
                return
            self.size_slider.finish()
            self.owner.save_preferences()
            if name == 'close':
                self.owner.close_menu()
            else:
                self.expanded = None if self.expanded == name else name
                self.row_gesture.cancel()
                if self.expanded == 'settings':
                    self.size_slider.paint()
                self.refresh()
        return callback

    def row_callback(self, group, key, phase):
        def callback(args):
            if phase == 'down':
                if self.row_gesture.touch is not None:
                    return
                self.pressed_row = (group,key,self.scroll(group).GetScrollViewPos())
                self.row_gesture.down(args,time.time())
            elif self.row_gesture.touch is not None and args.get('TouchId',0)!=self.row_gesture.touch[0]:
                return
            elif phase == 'move':
                self.row_gesture.move(args,1.)
            elif phase == 'cancel':
                self.row_gesture.cancel()
                self.pressed_row = None
            else:
                press = self.pressed_row
                self.pressed_row = None
                tap = self.row_gesture.up(args,time.time(),1.)
                if tap and press and press[:2] == (group,key) and abs(self.scroll(group).GetScrollViewPos()-press[2]) < 3.:
                    self.choose(group,key)
        return callback

    def choose(self, group, key):
        if group == 'settings':
            if self.expanded == 'settings' and self.owner.preferences.toggle(key):
                self.owner.save_preferences()
                self.refresh()
            return
        if key not in [item[0] for item in entries_for(self.owner.preferences.data['model'],group)]:
            return
        if group == 'models':
            self.owner.select_model(key)
        elif group == 'expressions':
            if key == 'stop':
                self.owner.effects.clear(time.time())
            else:
                self.owner.effects.select(key,time.time())
        elif key == 'stop':
            self.owner.stop_effect_motion()
        else:
            self.owner.play_effect_motion(key)
        self.expanded = None
        self.refresh()

    def layout(self):
        old_size = self.size
        super(CatMenu,self).layout()
        if self.size == old_size:
            return
        for group,entries in ENTRIES.items():
            height = MAX_VISIBLE_ROWS*ROW_HEIGHT
            control = self.GetBaseUIControl('/'+group)
            x = {'motions':98,'expressions':182,'models':266}[group]
            control.SetPosition((min(x,max(4,self.size[0]-LIST_WIDTH-8)),50))
            control.SetSize((LIST_WIDTH,min(height,max(30,self.size[1]-58))),True)
        self.UpdateScreen(True)

    def refresh(self):
        if not self.bound:
            return
        preferences = self.owner.preferences.data
        self.size_slider.paint()
        state = (self.owner.effects.expression,self.owner.effects.motion,self.expanded,preferences['model'])+tuple(
            preferences[key] for key in TOGGLE_KEYS)
        if preferences['model']=='deepseek':
            state += (tuple(self.owner.effects.runs),)
        if state == self.state:
            return
        self.state = state
        self.GetBaseUIControl('/settings').SetVisible(self.expanded == 'settings')
        self.GetBaseUIControl('/bar/settings/selected').SetVisible(self.expanded == 'settings')
        for key in TOGGLE_KEYS:
            active = preferences[key]
            path = self.contents['settings']+'/item_'+key
            self.GetBaseUIControl(path+'/selected').SetVisible(active)
            self.GetBaseUIControl(path+'/switch_knob').SetPosition((28 if active else 2,2))
            caption = self.GetBaseUIControl(path+'/text')
            caption.SetPosition((2 if active else 22,6))
            caption.asLabel().SetText(u'开' if active else u'关')
        for group,entries in ENTRIES.items():
            expanded = group == self.expanded
            self.GetBaseUIControl('/'+group).SetVisible(expanded)
            self.GetBaseUIControl('/bar/'+group+'/selected').SetVisible(expanded)
            active = state[0] if group == 'expressions' else state[1] if group == 'motions' else preferences['model']
            available = [e[0] for e in entries_for(preferences['model'],group)]
            content = self.GetBaseUIControl(self.contents[group])
            content.SetSize((LIST_WIDTH,max(MAX_VISIBLE_ROWS,len(available))*ROW_HEIGHT))
            for key, unused in entries:
                row = self.GetBaseUIControl(self.contents[group]+'/item_'+key)
                row.SetVisible(key in available)
                if key in available:
                    row.SetPosition((0,available.index(key)*ROW_HEIGHT))
                selected = self.owner.effects.is_selected(key) if group=='motions' and preferences['model']=='deepseek' else key == active
                self.GetBaseUIControl(self.contents[group]+'/item_'+key+'/selected').SetVisible(selected)
        self.UpdateScreen(True)

    def render_frame(self):
        super(CatMenu,self).render_frame()
        if self.created:self.size_slider.poll()

    def Update(self):
        # Native UI can send one final tick after a world/resource reload has
        # destroyed this screen or cleared its Python module globals.
        if not self.created or CatMenu is None:
            return
        self.bind_buttons()
        super(CatMenu,self).Update()
        self.refresh()

    def Destroy(self):
        self.size_slider.finish()
        self.owner.save_preferences()
        super(CatMenu,self).Destroy()
        if self.owner.menu is self:
            self.owner.menu = None
        self.owner.inputs.clear()
