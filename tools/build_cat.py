"""Compile the original cat's numeric meshes for a NetEase HUD (no image frames)."""
import json
import math
import uuid
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT/'addon/resource_pack'
BP = ROOT/'addon/behavior_pack'
SRC = ROOT/'assets/source/standard'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


def encode(values, lo, hi):
    values = np.asarray(values, dtype=float)
    assert np.isfinite(values).all()
    assert values.min() >= lo-1e-5 and values.max() <= hi+1e-5
    q = np.rint((np.clip(values, lo, hi)-lo)/(hi-lo)*65535).astype(np.uint32)
    out = np.empty(q.shape[:-1]+(4,), np.uint8)
    out[..., 0] = q[..., 0] >> 8
    out[..., 1] = q[..., 0] & 255
    out[..., 2] = q[..., 1] >> 8
    out[..., 3] = q[..., 1] & 255
    return out


def atlas_uv(uv, texture):
    uv = np.array(uv, dtype=float).reshape(-1, 2).copy()
    uv[:, 0] *= .5
    uv[:, 1] = (1-uv[:, 1]+texture)*.25
    return uv


def premultiply_rgba(image):
    """Filter premultiplied colour so transparent black cannot darken joins."""
    pixels = np.array(image.convert('RGBA'), dtype=np.uint16)
    pixels[..., :3] = (pixels[..., :3]*pixels[..., 3:4]+127)//255
    return Image.fromarray(pixels.astype(np.uint8))


def key_placements(keys):
    """Trim alpha-zero margins only; pack every visible source pixel at 1:1."""
    records = []
    for path in keys:
        image = Image.open(path).convert('RGBA')
        assert image.size == (612,354), 'Unexpected key canvas: '+str(path)
        bounds = image.getchannel('A').getbbox()
        assert bounds is not None, 'Empty key art: '+str(path)
        records.append({'name':path.stem,'canvas_bounds':list(bounds),
                        'size':[bounds[2]-bounds[0],bounds[3]-bounds[1]]})
    x,y,row_height = 1026,2,0
    for record in sorted(records,key=lambda item:-item['size'][1]):
        w,h = record['size']
        if x+w+2 > 2048:
            x,y,row_height = 1026,y+row_height+4,0
        assert y+h+2 <= 2048, 'Native key art exceeds atlas capacity'
        record['atlas_origin'] = [x,y]
        x += w+4
        row_height = max(row_height,h)
    return records


def inverse_uv(points, mask_points, mask_uv, triangles):
    tri = mask_points[:, triangles, :]
    a = tri[:, :, 0, :]
    b = tri[:, :, 1, :]-a
    c = tri[:, :, 2, :]-a
    q = points[:, :, None, :]-a[:, None, :, :]
    det = b[:, :, 0]*c[:, :, 1]-b[:, :, 1]*c[:, :, 0]
    valid = np.abs(det)>1e-10
    safe = np.where(valid, det, 1.)
    u = (q[:, :, :, 0]*c[:, None, :, 1]-q[:, :, :, 1]*c[:, None, :, 0])/safe[:, None, :]
    v = (b[:, None, :, 0]*q[:, :, :, 1]-b[:, None, :, 1]*q[:, :, :, 0])/safe[:, None, :]
    w = 1-u-v
    cost = np.maximum(-u, 0)**2+np.maximum(-v, 0)**2+np.maximum(-w, 0)**2
    cost += np.where(valid[:, None, :], 0, 1e10)
    best = np.argmin(cost, axis=2)
    weights = np.stack([np.take_along_axis(t, best[:, :, None], axis=2)[:, :, 0] for t in (w, u, v)], axis=2)
    return np.clip((weights[:, :, :, None]*mask_uv[triangles][best]).sum(axis=2), -2, 2)


def build_assets():
    from sync_license_notices import sync
    sync()
    model = json.loads((ROOT/'build/model.json').read_text())
    n = model['vertexCount']; ds = model['drawables']; nd = len(ds)
    frames = np.fromfile(ROOT/'build/poses.f32', dtype='<f4').reshape(model['poseCount'], model['stride'])
    positions = frames[:, :n*2].reshape(-1, n, 2)
    orders = frames[:, n*2+nd:]
    assert np.all(orders == orders[0]), 'Draw order changed; needs dynamic order handling'
    offset = masked = 0
    for d in ds:
        d['offset'] = offset; offset += d['vertexCount']
        d['maskOffset'] = masked
        if d['masks']: masked += d['vertexCount']
    stride = n+nd+masked
    width = 1024
    height = 2**math.ceil(math.log2(math.ceil(stride*len(frames)/width)))
    packed = np.zeros((len(frames), stride, 4), np.uint8)
    packed[:, :n] = encode(positions, -4, 4)
    opacity = np.clip(frames[:, n*2:n*2+nd], 0, 1)
    packed[:, n:n+nd] = encode(np.stack([opacity, np.zeros_like(opacity)], axis=2), 0, 1)
    keys = sorted((SRC/'resources/left-keys').glob('*.png'))
    key_rects = key_placements(keys)
    meta = np.zeros((n*4+len(keys)*3, 4), np.uint8)
    for i, record in enumerate(key_rects):
        descriptor = [record['atlas_origin'],record['canvas_bounds'][:2],record['size']]
        meta[n*4+i*3:n*4+i*3+3] = encode(descriptor,0,65535)
    vertices = []; indices = []
    for di, d in enumerate(ds):
        start = d['offset']; nv = d['vertexCount']
        uv = atlas_uv(d['uvs'], d['texture'])
        minuv = np.zeros(2); maxuv = np.ones(2)
        if d['masks']:
            assert len(d['masks']) == 1
            mask = ds[d['masks'][0]]; ms = mask['offset']; mn = mask['vertexCount']
            muv = atlas_uv(mask['uvs'], mask['texture'])
            minuv = muv.min(axis=0); maxuv = muv.max(axis=0)
            mapping = inverse_uv(positions[:, start:start+nv], positions[:, ms:ms+mn], muv, np.array(mask['indices']).reshape(-1, 3))
            packed[:, n+nd+d['maskOffset']:n+nd+d['maskOffset']+nv] = encode(mapping, -2, 2)
        for local in range(nv):
            vi = start+local; mi = vi*4
            meta[mi] = encode(uv[local:local+1], 0, 1)[0]
            meta[mi+1] = [di, d['maskOffset']+local+1 if d['masks'] else 0, 1 if d['flags'] & 8 else 0, d['effect']]
            meta[mi+2] = encode(minuv[None, :], 0, 1)[0]
            meta[mi+3] = encode(maxuv[None, :], 0, 1)[0]
            vertices.append({'pos':[0,16,0], 'normal':[0,0,-1], 'uvcoord':[vi/512.,0], 'weight':[['root',1.]]})
    for di in np.argsort(orders[0]):
        d = ds[di]
        indices.extend((np.array(d['indices']).reshape(-1,3)+d['offset']).tolist())
    # The original app supplies keyboard-down paw images separately from the MOC.
    for x,y in ((0,0),(1,0),(1,1),(0,1)):
        vertices.append({'pos':[0,16,0], 'normal':[0,0,-1], 'uvcoord':[x,.5+.1*y], 'weight':[['root',1.]]})
    indices.extend([[n,n+1,n+2],[n,n+2,n+3]])
    for x,y in ((0,0),(1,0),(1,1),(0,1)):
        vertices.append({'pos':[0,16,0], 'normal':[0,0,-1], 'uvcoord':[x,.8+.1*y], 'weight':[['root',1.]]})
    indices = [[n+4,n+5,n+6],[n+4,n+6,n+7]]+indices
    tex = RP/'textures/models/bongocatmc'; tex.mkdir(parents=True, exist_ok=True)
    flat = np.zeros((width*height,4),np.uint8); flat[:stride*len(frames)] = packed.reshape(-1,4)
    Image.fromarray(flat.reshape(height,width,4)).save(tex/'poses.png')
    mh = 2**math.ceil(math.log2(math.ceil(len(meta)/512)))
    mt = np.zeros((mh*512,4),np.uint8); mt[:len(meta)] = meta
    Image.fromarray(mt.reshape(mh,512,4)).save(tex/'meta.png')
    atlas = Image.new('RGBA',(2048,2048))
    for i in range(3): atlas.paste(Image.open(SRC/('demomodel.1024/texture_%02d.png'%i)),(0,i*512))
    atlas.paste(Image.open(SRC/'resources/background.png'),(0,1536))
    for path, record in zip(keys,key_rects):
        crop = Image.open(path).convert('RGBA').crop(record['canvas_bounds'])
        atlas.paste(crop,tuple(record['atlas_origin']))
    # Both model and keyboard paw use the same premultiplied blend convention.
    # Numeric data textures above are NOT colours and must remain unmodified.
    premultiply_rgba(atlas).save(tex/'atlas.png')
    save(RP/'models/bongocatmc/cat_mesh.json', {'mesh':[{'material':'bongocatmc/cat','vertices':vertices,'indices':indices}]})
    bounds = [[-24,-8,-1],[24,40,1]]
    save(RP/'models/bongocatmc/cat_skeleton.json', {'skeleton':[{'name':'root','parent':'root','initpos':[0,0,0], 'initquaternion':[0,0,0,1], 'initscale':[1,1,1], 'offmtx':[[1,0,0,0],[0,1,0,0],[0,0,1,0]], 'boundingbox':bounds}],'boundingbox':bounds})
    models_path = RP/'models/netease_models.json'
    models = json.loads(models_path.read_text()) if models_path.exists() else {}
    models['bongocatmc_default'] = {'dy_load':True,'mesh':'bongocatmc/cat_mesh.json','skeleton':'bongocatmc/cat_skeleton.json','animation':{},'material':'bongocatmc_mesh','texture':{'tex0':'bongocatmc/atlas','tex1':'bongocatmc/poses','tex2':'bongocatmc/meta'}}
    save(models_path,models)
    materials_path = RP/'materials/entity.material'
    materials = json.loads(materials_path.read_text()) if materials_path.exists() else {'materials':{'version':'1.0.0'}}
    materials['materials']['bongocatmc_mesh:entity_for_skeleton'] = {'vertexShader':'shaders/glsl/bongocatmc.vertex','fragmentShader':'shaders/glsl/bongocatmc.fragment','states':['Blending','DisableCulling','DisableDepthWrite','DisableDepthTest'],'blendSrc':'One','blendDst':'OneMinusSrcAlpha','msaaSupport':'Both','+samplerStates':[{'samplerIndex':i,'textureFilter':'Bilinear' if i==0 else 'Point'} for i in range(3)]}
    save(materials_path,materials)
    shader = RP/'shaders/glsl'; shader.mkdir(parents=True,exist_ok=True)
    (shader/'bongocatmc_data.h').write_text('\n'.join('#define %s %.1f'%(k,v) for k,v in [('STRIDE',stride),('DATA_W',width),('DATA_H',height),('META_H',mh),('VERTICES',n),('DRAWABLES',nd),('KEY_META',n*4)])+'\n',encoding='utf8')
    with (shader/'bongocatmc_data.h').open('a',encoding='utf8') as f:
        for name, bank in model['banks'].items():
            f.write('#define BANK_%s %.1f\n'%(name.upper(),bank['start']))
            f.write('#define STEPS_%s %.1f\n'%(name.upper(),bank['count']-1))
    client = BP/'bongocat_mod/client'; client.mkdir(parents=True,exist_ok=True)
    (client/'data.py').write_text('# Generated key art indices\nKEY_ART = '+repr({p.stem:i for i,p in enumerate(keys)})+'\n',encoding='utf8')
    motions = {name:json.loads((SRC/('live2d_motion%d.motion3.json'%i)).read_text()) for i,name in [(1,'flash'),(2,'wave')]}
    (client/'motion_data.py').write_text('# Original Cubism motion curves\nMOTIONS = '+repr(motions)+'\n',encoding='utf8')
    from submission_audio import write_audio
    audio = RP/'sounds/bongocatmc'; audio.mkdir(parents=True,exist_ok=True)
    write_audio(SRC/'live2d_motion1.flac', audio/'lightning.ogg')
    sounds_path = RP/'sounds/sound_definitions.json'
    sounds = json.loads(sounds_path.read_text()) if sounds_path.exists() else {}
    sounds['bongocatmc.lightning'] = {'category':'ui','sounds':[{'name':'sounds/bongocatmc/lightning','stream':False}]}
    save(sounds_path,sounds)
    save(ROOT/'diagnostics/build_report.json', {'vertices':n,'triangles':len(indices),'poses':len(frames),'masked_vertices':masked,'key_overlays':len(keys),'texture_bytes':sum(p.stat().st_size for p in tex.glob('*.png')),'key_source_scale':1,'key_rects':key_rects})


def build_ui():
    from sync_license_notices import sync
    sync()
    actor = {'type':'custom','renderer':'netease_paper_doll_renderer','skeleton_model_name':'','animation':'','animation_looped':False,'rotation':'gesture_x','screen_scale':1.,'init_rot_y':0,'enable_scissor_test':False,'clips_children':False,'layer':1,'size':[180,140],'anchor_from':'top_left','anchor_to':'top_left','offset':[0,0]}
    from build_menu import menu_definitions, touch_button
    ui = {'namespace':'bongocatmc','hud':{'type':'screen','is_showing_menu':False,'absorbs_input':False,'is_modal':False,'should_steal_mouse':False,'render_game_behind':True,'controls':[{'root':{'type':'panel','size':['100%','100%'],'controls':[{'actor':actor},{'touch':touch_button()}]}}]}}
    ui.update(menu_definitions(actor))
    save(RP/'ui/bongocatmc.json', ui)
    save(RP/'ui/_ui_defs.json', {'ui_defs':['ui/bongocatmc.json']})
    rid = 'c34da1b3-212b-4d38-acaa-d0d243e131da'; bid = '09e4aefb-93c4-4408-b072-f3f2221c043a'
    for folder, ident, kind in ((RP,rid,'resources'),(BP,bid,'data')):
        manifest = {'format_version':1,'header':{'name':'BongoCatMC','description':'Default cat gameplay HUD prototype','uuid':ident,'version':[0,1,0],'min_engine_version':[1,18,0]},'modules':[{'type':kind,'uuid':str(uuid.uuid5(uuid.UUID(ident),'module')),'version':[0,1,0]}]}
        if kind=='data': manifest['dependencies']=[{'uuid':rid,'version':[0,1,0]}]
        save(folder/'manifest.json',manifest)


if __name__ == '__main__':
    build_assets()
    build_ui()
    report = json.loads((ROOT/'diagnostics/build_report.json').read_text())
    print(json.dumps({key:value for key,value in report.items() if key != 'key_rects'},indent=2))
