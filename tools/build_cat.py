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
    packed[:, :n] = encode(positions, -2, 2)
    opacity = np.clip(frames[:, n*2:n*2+nd], 0, 1)
    packed[:, n:n+nd] = encode(np.stack([opacity, np.zeros_like(opacity)], axis=2), 0, 1)
    meta = np.zeros((n*4, 4), np.uint8)
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
            meta[mi+1] = [di, d['maskOffset']+local+1 if d['masks'] else 0, 1 if d['flags'] & 8 else 0, 255]
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
    keys = sorted((SRC/'resources/left-keys').glob('*.png'))
    for i,p in enumerate(keys):
        atlas.paste(Image.open(p).resize((204,118),Image.Resampling.LANCZOS),(1024+(i%5)*204,(i//5)*118))
    atlas.save(tex/'atlas.png')
    save(RP/'models/bongocatmc/cat_mesh.json', {'mesh':[{'material':'bongocatmc/cat','vertices':vertices,'indices':indices}]})
    bounds = [[-24,-8,-1],[24,40,1]]
    save(RP/'models/bongocatmc/cat_skeleton.json', {'skeleton':[{'name':'root','parent':'root','initpos':[0,0,0], 'initquaternion':[0,0,0,1], 'initscale':[1,1,1], 'offmtx':[[1,0,0,0],[0,1,0,0],[0,0,1,0]], 'boundingbox':bounds}],'boundingbox':bounds})
    save(RP/'models/netease_models.json', {'bongocatmc_default':{'dy_load':True,'mesh':'bongocatmc/cat_mesh.json','skeleton':'bongocatmc/cat_skeleton.json','animation':{},'material':'bongocatmc_mesh','texture':{'tex0':'bongocatmc/atlas','tex1':'bongocatmc/poses','tex2':'bongocatmc/meta'}}})
    save(RP/'materials/entity.material', {'materials':{'version':'1.0.0','bongocatmc_mesh:entity_for_skeleton':{'vertexShader':'shaders/glsl/bongocatmc.vertex','fragmentShader':'shaders/glsl/bongocatmc.fragment','states':['Blending','DisableCulling','DisableDepthWrite','DisableDepthTest'],'blendSrc':'SourceAlpha','blendDst':'OneMinusSrcAlpha','msaaSupport':'Both','+samplerStates':[{'samplerIndex':i,'textureFilter':'Bilinear' if i==0 else 'Point'} for i in range(3)]}}})
    shader = RP/'shaders/glsl'; shader.mkdir(parents=True,exist_ok=True)
    (shader/'bongocatmc_data.h').write_text('\n'.join('#define %s %.1f'%(k,v) for k,v in [('STRIDE',stride),('DATA_W',width),('DATA_H',height),('META_H',mh),('VERTICES',n),('DRAWABLES',nd)])+'\n',encoding='utf8')
    client = BP/'bongocat_mod/client'; client.mkdir(parents=True,exist_ok=True)
    (client/'data.py').write_text('# Generated key art indices\nKEY_ART = '+repr({p.stem:i for i,p in enumerate(keys)})+'\n',encoding='utf8')
    save(ROOT/'diagnostics/build_report.json', {'vertices':n,'triangles':len(indices),'poses':len(frames),'masked_vertices':masked,'key_overlays':len(keys),'texture_bytes':sum(p.stat().st_size for p in tex.glob('*.png'))})


def build_ui():
    actor = {'type':'custom','renderer':'netease_paper_doll_renderer','skeleton_model_name':'','animation':'','animation_looped':False,'rotation':'gesture_x','screen_scale':1.,'init_rot_y':0,'enable_scissor_test':False,'clips_children':False,'layer':1,'size':[180,140],'anchor_from':'top_left','anchor_to':'top_left','offset':[0,0]}
    save(RP/'ui/bongocatmc.json', {'namespace':'bongocatmc','hud':{'type':'screen','is_showing_menu':False,'absorbs_input':False,'is_modal':False,'should_steal_mouse':False,'render_game_behind':True,'controls':[{'root':{'type':'panel','size':['100%','100%'],'controls':[{'actor':actor}]}}]}})
    save(RP/'ui/_ui_defs.json', {'ui_defs':['ui/bongocatmc.json']})
    rid = 'd08f140d-c9dd-4f65-986b-ef3908b03c46'; bid = 'c2df7ba3-c4ac-41f1-bfd7-d40c3cd75a49'
    for folder, ident, kind in ((RP,rid,'resources'),(BP,bid,'data')):
        manifest = {'format_version':1,'header':{'name':'BongoCatMC','description':'Default cat gameplay HUD prototype','uuid':ident,'version':[0,1,0],'min_engine_version':[1,18,0]},'modules':[{'type':kind,'uuid':str(uuid.uuid5(uuid.UUID(ident),'module')),'version':[0,1,0]}]}
        if kind=='data': manifest['dependencies']=[{'uuid':rid,'version':[0,1,0]}]
        save(folder/'manifest.json',manifest)


if __name__ == '__main__':
    build_assets()
    build_ui()
    print((ROOT/'diagnostics/build_report.json').read_text())
