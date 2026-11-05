"""Compare original per-pixel Cubism masks against the compiled mask mapping."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from build_cat import ROOT, SRC, inverse_uv


def sample(texture, uv):
    h,w=texture.shape[:2]
    p=uv*np.array([w,h])-.5
    low=np.floor(p).astype(int); t=p-low
    x0=np.clip(low[...,0],0,w-1); x1=np.clip(low[...,0]+1,0,w-1)
    y0=np.clip(low[...,1],0,h-1); y1=np.clip(low[...,1]+1,0,h-1)
    return ((texture[y0,x0]*(1-t[...,0,None])+texture[y0,x1]*t[...,0,None])*(1-t[...,1,None])+
            (texture[y1,x0]*(1-t[...,0,None])+texture[y1,x1]*t[...,0,None])*t[...,1,None])


def raster(points,uv,indices,texture,bounds=None):
    points=points*np.array([354,-354])+np.array([306,177])
    out=np.zeros((354,612,4),float)
    for ids in indices:
        tri=points[ids]; a=tri[0]; b=tri[1]-a; c=tri[2]-a
        det=b[0]*c[1]-b[1]*c[0]
        if abs(det)<1e-8:continue
        x0,y0=np.maximum(0,np.floor(tri.min(axis=0)).astype(int))
        x1,y1=np.minimum([612,354],np.ceil(tri.max(axis=0)).astype(int))
        if x0>=x1 or y0>=y1:continue
        yy,xx=np.mgrid[y0:y1,x0:x1]
        q=np.stack([xx+.5,yy+.5],axis=-1)-a
        u=(q[...,0]*c[1]-q[...,1]*c[0])/det
        v=(b[0]*q[...,1]-b[1]*q[...,0])/det
        w=1-u-v
        inside=(u>=-1e-7)&(v>=-1e-7)&(w>=-1e-7)
        coords=w[...,None]*uv[ids[0]]+u[...,None]*uv[ids[1]]+v[...,None]*uv[ids[2]]
        colors=sample(texture,coords)
        if bounds is not None:
            colors[...,3]*=np.all((coords>=bounds[0])&(coords<=bounds[1]),axis=-1)
        out[y0:y1,x0:x1][inside]=colors[inside]
    return out


def over(canvas, layer):
    alpha=layer[...,3:4]
    canvas[...,:3]=layer[...,:3]*alpha+canvas[...,:3]*(1-alpha)
    canvas[...,3:4]=alpha+canvas[...,3:4]*(1-alpha)


def render(frame=112,key='KeyW',approximate=False,premultiplied=False):
    model=json.loads((ROOT/'build/model.json').read_text()); n=model['vertexCount']; ds=model['drawables']
    f=np.fromfile(ROOT/'build/poses.f32',dtype='<f4').reshape(model['poseCount'],model['stride'])[frame]
    points=f[:n*2].reshape(n,2); textures=[np.asarray(Image.open(SRC/('demomodel.1024/texture_%02d.png'%i)).convert('RGBA'),float)/255 for i in range(3)]
    parts=[]; start=0
    for d in ds:
        p=points[start:start+d['vertexCount']]; start+=d['vertexCount']
        uv=np.asarray(d['uvs']).reshape(-1,2).copy(); uv[:,1]=1-uv[:,1]
        ix=np.asarray(d['indices']).reshape(-1,3)
        parts.append((p,uv,ix,textures[d['texture']]))
    layers=[raster(*part) for part in parts]
    canvas=np.asarray(Image.open(SRC/'resources/background.png').convert('RGBA'),float)/255
    canvas[...,:3]*=canvas[...,3:4]
    for i in np.argsort(f[n*2+len(ds):]):
        opacity=np.clip(f[n*2+i],0,1)
        if opacity<.001:continue
        layer=layers[i].copy(); layer[...,3]*=opacity
        if ds[i]['masks']:
            mask=ds[i]['masks'][0]
            if approximate:
                p,uv,ix,tex=parts[mask]
                mapping=inverse_uv(parts[i][0][None],p[None],uv,ix)[0]
                coverage=raster(parts[i][0],mapping,parts[i][2],tex,(uv.min(axis=0),uv.max(axis=0)))[...,3]
            else:coverage=layers[mask][...,3]
            layer[...,3]*=1-coverage if ds[i]['flags']&8 else coverage
        over(canvas,layer)
    if model['records'][frame].get('key'):
        im=Image.open(SRC/('resources/left-keys/'+key+'.png')).convert('RGBA')
        if approximate:im=im.resize((204,118),Image.Resampling.LANCZOS)
        texture=np.asarray(im,float)/255
        if premultiplied:texture[...,:3]*=texture[...,3:4]
        yy,xx=np.mgrid[0:354,0:612]
        overlay=sample(texture,np.stack([(xx+.5)/612,(yy+.5)/354],axis=-1))
        if premultiplied:overlay[...,:3]/=np.maximum(overlay[...,3:4],1e-10)
        over(canvas,overlay)
    return canvas


if __name__=='__main__':
    out=ROOT/'diagnostics/paw_seam';out.mkdir(parents=True,exist_ok=True)
    for frame in (112,100,124):
        for name,approximate,premultiplied in [('original',False,True),('before',True,False),('fixed',True,True)]:
            canvas=render(frame,approximate=approximate,premultiplied=premultiplied)
            # Composite against grey to make transparent gaps visible.
            canvas[...,:3]+=.35*(1-canvas[...,3:4]);canvas[...,3]=1
            Image.fromarray(np.rint(np.clip(canvas,0,1)*255).astype('uint8')).save(out/('%d_%s.png'%(frame,name)))
    print(str(out))
