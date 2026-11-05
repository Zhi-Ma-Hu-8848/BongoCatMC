"""Compact toolbar with native mouse/touch scrolling dropdowns."""
from pathlib import Path
import runpy
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CATALOG = runpy.run_path(str(ROOT/'addon/behavior_pack/bongocat_mod/client/menu_catalog.py'))

def rect(x,y,w,h):
    return {'anchor_from':'top_left','anchor_to':'top_left','offset':[x,y],'size':[w,h]}

def label(text,x,y,w,h):
    # Native normal-font glyphs occupy the top of the label's line box.
    # Offset the baseline so the visible text centres on buttons and rows.
    return dict(type='label',text=text,color=[.34,.16,.26],font_size='normal',text_alignment='center',shadow=False,layer=4,**rect(x,y+4,w,h))

def touch_button():
    return dict(type='button',layer=10,controls=[],button_mappings=[{'from_button_id':'button.menu_select','to_button_id':'button.click','mapping_type':'pressed'}],**rect(0,0,1,1))

def surface(texture,layer=0):
    return {'type':'image','texture':'textures/ui/bongocatmc/pink_'+texture,'size':['100%','100%'],
            'keep_ratio':False,'nineslice_size':4,'layer':layer}

def button(text,x,y,w,h):
    b=touch_button();b.update(rect(x,y,w,h))
    b.update(default_control='normal',hover_control='hover',pressed_control='pressed')
    b['controls']=[{state:surface(tex,1)} for state,tex in [('normal','button'),('hover','hover'),('pressed','pressed')]]
    b['controls'] += [{'selected':dict(surface('pressed',2),visible=False)}, {'text':label(text,0,(h-16)/2,w,16)}]
    return b

def dropdown_content(entries):
    width=CATALOG['LIST_WIDTH'];row=CATALOG['ROW_HEIGHT']
    return dict(type='panel',controls=[{'item_'+key:button(name,0,i*row,width,row)} for i,(key,name) in enumerate(entries)],**rect(0,0,width,len(entries)*row))


def scrolling_list(content,width,height):
    scroll=dict(layer=2,**rect(0,0,width,height))
    scroll.update({'$touch':True,'$scrolling_content':content,
        '$scrolling_pane_size':[width,height],'$scrolling_pane_size_touch':[width,height],
        '$scroll_view_control_size':[width,height],'$view_port_size_touch':[width,height],
        '$scroll_view_port_size_touch':[width,height],'$scroll_view_port_max_size_touch':[width,height],
        '$scroll_view_port_panel_size':[width,height],'$scroll_bar_contained_touch':True,
        '$scroll_box_visible_touch':False,'$scroll_size_touch':[0,height],'$show_background':False,
        '$scroll_bar_left_padding_size_touch':[0,0],'$scroll_bar_right_padding_size_touch':[0,0]})
    return scroll

def menu_definitions(actor):
    textures=ROOT/'addon/resource_pack/textures/ui/bongocatmc'
    textures.mkdir(parents=True,exist_ok=True)
    for name,color in [('panel',(255,239,246,250)),('button',(255,222,236,250)),('hover',(255,202,225,255)),('pressed',(239,155,193,255))]:
        im=Image.new('RGBA',(16,16));draw=ImageDraw.Draw(im)
        draw.rounded_rectangle((0,0,15,15),radius=3,fill=color,outline=(202,113,155,255))
        im.save(textures/('pink_'+name+'.png'))
    controls=[{'root':{'type':'panel','size':['100%','100%'],'controls':[{'actor':actor},{'touch':touch_button()}]}}]
    controls.append({'outside':dict(touch_button(),size=['100%','100%'],layer=10)})
    bar=[{key:button(text,i*84,0,78,30)} for i,(key,text) in enumerate([('settings','设置'),('motions','动作'),('expressions','表情'),('models','模型')])]
    controls.append({'bar':dict(type='panel',layer=30,controls=bar,**rect(14,14,330,30))})
    close=button('退出',-14,14,78,30)
    close.update(anchor_from='top_right',anchor_to='top_right',layer=30)
    controls.append({'close':close})
    result={'settings_content':settings_content()}
    controls.append({'settings':settings_panel()})
    for group,entries in CATALOG['ENTRIES'].items():
        width=CATALOG['LIST_WIDTH'];height=CATALOG['MAX_VISIBLE_ROWS']*CATALOG['ROW_HEIGHT']
        scroll=scrolling_list('bongocatmc.'+group+'_content',width,height)
        controls.append({group:dict(type='panel',layer=40,visible=False,controls=[{'bg':surface('panel')},{'list@common.scrolling_panel':scroll}],**rect({'motions':98,'expressions':182,'models':266}[group],50,width,height))})
        result[group+'_content']=dropdown_content(entries)
    result['menu']={'type':'screen','is_showing_menu':True,'absorbs_input':True,'is_modal':True,'should_steal_mouse':True,'render_game_behind':True,'controls':controls}
    return result


def settings_panel():
    # Alpha is opacity: 0.30 leaves the game world 70% visible underneath.
    bg=surface('panel');bg.update(alpha=.30)
    scroll=scrolling_list('bongocatmc.settings_content',246,168)
    scroll['$allow_scrolling_even_when_content_fits']=False
    return dict(type='panel',visible=False,layer=30,controls=[{'bg':bg},
        {'list@common.scrolling_panel':scroll}],**rect(14,48,246,168))


def settings_content():
    entries=[('size','大小')]
    controls=[]
    for i,(key,title) in enumerate(entries):
        y=9+i*36
        title_art=label(title,16,y,30,18)
        title_art['text_alignment']='left'
        value_art=label('100%',194,y,44,18)
        for art in (title_art,value_art):
            art.update(color=[1.,.92,.97],shadow=True,font_scale_factor=1.1)
        controls += [{key+'_label':title_art},{key+'_value':value_art}]
        slider=touch_button()
        # Keep a comfortable touch target around the thinner visible track.
        slider.update(rect(50,y-3,140,24))
        slider['controls']=[
            # ScrollView resolves its native "track" by descendant name.
            # A content image with that name can be mistaken for ScrollTrack.
            {'size_rail_image':dict(surface('button',1),**rect(0,10,140,4))},
            {'fill':dict(surface('pressed',2),**rect(0,10,49,4))},
            {'thumb':dict(surface('panel',3),**rect(42,4,14,16))}]
        controls.append({key:slider})
    toggles=[('flip_vertical','上下镜像'),('flip_horizontal','左右镜像'),('mouse_recenter','鼠标回正')]
    for i,(key,title) in enumerate(toggles,len(entries)):
        y=9+i*36
        caption=label(title,16,y,100,18)
        caption.update(color=[1.,.92,.97],shadow=True,font_scale_factor=1.1,text_alignment='left')
        switch=button('关',194,y-1,44,20)
        switch['controls'].append({'switch_knob':dict(surface('panel',5),**rect(2,2,14,16))})
        for child in switch['controls']:
            if 'text' in child:child['text'].update(rect(22,6,20,16))
        controls += [{key+'_label':caption},{'item_'+key:switch}]
    return dict(type='panel',controls=controls,**rect(0,0,246,max(168,(len(entries)+len(toggles))*36)))
