"""Assemble continuous Cubism parameter tables with Core comparison checks."""
import json,math,itertools
from pathlib import Path
import numpy as np
from PIL import Image
from build_cat import ROOT,RP,BP,encode,save,inverse_uv

FOLDER=ROOT/'build/deepseek_parameters'
SRC=ROOT/'assets/source/deepseek/img/standard/cat_model'

def interpolate(data,record,values,params):
    count=record['counts'];coord=[(values[p]-params[p]['min'])/(params[p]['max']-params[p]['min'])*(c-1) for p,c in zip(record['dims'],count)]
    lo=np.floor(coord).astype(int);hi=np.ceil(coord).astype(int);t=np.array(coord)-lo
    shape=data.shape[1:];result=np.zeros(shape)
    for flags in itertools.product((0,1),repeat=len(count)):
        at=0;stride=1;weight=1.
        for i,flag in enumerate(flags):
            at+=(hi[i] if flag else lo[i])*stride;stride*=count[i];weight*=t[i] if flag else 1-t[i]
        result+=data[at]*weight
    return result

def build():
    model=json.loads((FOLDER/'model.json').read_text());ds=model['drawables'];params=model['params'];nd=len(ds)
    raw=np.memmap(FOLDER/'samples.f32',dtype='<f4',mode='r');tables={};records={}
    for record in model['records']:
        di=record['di'];kind=record['kind'];d=ds[di];nv=d['vertexCount'];start=record['floatOffset']
        a=np.array(raw[start:start+record['num']*record['stride']]).reshape(record['num'],-1,2)
        if kind=='outer':
            if d['outer'] and record['dims']:
                base=np.array(d['base']).reshape(-1,2);design=np.c_[base,np.ones(nv)];inverse=np.linalg.pinv(design)
                a=np.einsum('ij,fjk->fik',inverse,a)
            else:a=np.array([[[1.,0.],[0.,1.],[0.,0.]]])
        elif kind=='mask':
            mask=ds[d['masks'][0]];muv=np.array(mask['uvs']).reshape(-1,2);muv[:,1]=1-muv[:,1]
            result=np.zeros((record['num'],nv,2),np.float32)
            for first in range(0,len(a),8):
                result[first:first+8]=inverse_uv(a[first:first+8,:nv],a[first:first+8,nv:],muv,np.array(mask['indices']).reshape(-1,3))
            a=result
        tables[di,kind]=a;records[di,kind]=record
    # Validate independent combinations, including simultaneous blink/physics/props.
    n=sum(d['vertexCount'] for d in ds);checks=np.fromfile(FOLDER/'validation.f32',dtype='<f4').reshape(len(model['checks']),n*2+nd)
    errors=[];opacity_error=0.;offset=0
    for di,d in enumerate(ds):
        peak=0.;nv=d['vertexCount']
        for k,values in enumerate(model['checks']):
            local=interpolate(tables[di,'position'],records[di,'position'],values,params)
            matrix=interpolate(tables[di,'outer'],records[di,'outer'],values,params)
            predicted=np.c_[local,np.ones(nv)]@matrix
            actual=checks[k,offset*2:(offset+nv)*2].reshape(-1,2)
            if checks[k,n*2+di]>.01:peak=max(peak,float(np.linalg.norm(predicted-actual,axis=1).max())*1024)
            opacity_error=max(opacity_error,abs(float(interpolate(tables[di,'opacity'],records[di,'opacity'],values,params)[0,0])-float(checks[k,n*2+di])))
        errors.append((peak,d['id']));offset+=nv
    print('Core comparison source pixels:',sorted(errors,reverse=True)[:8],'opacity',opacity_error,flush=True)
    save(ROOT/'diagnostics/deepseek_parameter_validation.json',{'max_source_pixel_error':max(e[0] for e in errors),'parts':sorted(errors,reverse=True),'opacity_error':opacity_error,'samples':len(checks)})
    assert max(e[0] for e in errors)<3., 'Refine deformation lattice before publishing'
    assert opacity_error<.015
    # Keep original atlas, original hand placement and its premultiplied pixels.
    keys=json.loads((ROOT/'diagnostics/deepseek_build.json').read_text())['keys']
    draw_meta=n*2;key_meta=draw_meta+nd*20;param_meta=key_meta+len(keys)*3
    meta=np.zeros((param_meta+len(params),4),np.uint8);blocks=[];cursor=0
    def descriptor(di,kind,address):
        nonlocal cursor
        a=tables[di,kind];r=records[di,kind];block=encode(a,-2,2).reshape(-1,4)
        meta[address]=[cursor&255,(cursor>>8)&255,(cursor>>16)&255,255]
        meta[address+1]=r['dims']+[255]*(4-len(r['dims']))
        meta[address+2]=r['counts']+[1]*(4-len(r['counts']))
        meta[address+3]=encode([[a.shape[1],0]],0,65535)[0]
        blocks.append(block);cursor+=len(block)
    vertices=[];indices=[];offset=0
    for di,d in enumerate(ds):
        d['offset']=offset;nv=d['vertexCount'];uv=np.array(d['uvs']).reshape(-1,2);uv[:,1]=1-uv[:,1]
        for j in range(nv):
            vi=offset+j;meta[vi*2]=encode(uv[j:j+1],0,1)[0];meta[vi*2+1]=encode([[di,j]],0,65535)[0]
            vertices.append({'pos':[0,16,0],'normal':[0,0,-1],'uvcoord':[vi/8192.,0],'weight':[['root',1.]]})
        at=draw_meta+di*20
        for slot,kind in enumerate(('position','outer','opacity')):descriptor(di,kind,at+slot*4)
        if d['masks']:
            descriptor(di,'mask',at+12);uvmask=np.array(ds[d['masks'][0]]['uvs']).reshape(-1,2);uvmask[:,1]=1-uvmask[:,1]
            meta[at+16]=encode(uvmask.min(axis=0)[None,:],0,1)[0];meta[at+17]=encode(uvmask.max(axis=0)[None,:],0,1)[0]
        meta[at+18]=[bool(d['masks']),bool(d['flags']&8),0,255];offset+=nv
    for d in sorted(ds,key=lambda d:d['order']):indices.extend((np.array(d['indices']).reshape(-1,3)+d['offset']).tolist())
    for i,r in enumerate(keys):meta[key_meta+i*3:key_meta+i*3+3]=encode([r['origin'],r['box'][:2],r['size']],0,65535)
    for i,p in enumerate(params):meta[param_meta+i]=[p['min']==-p['max'],0,0,255]
    for x,y in ((0,0),(1,0),(1,1),(0,1)):vertices.append({'pos':[0,16,0],'normal':[0,0,-1],'uvcoord':[x,.5+.1*y],'weight':[['root',1.]]})
    indices.extend([[n,n+1,n+2],[n,n+2,n+3]])
    tex=RP/'textures/models/bongocatmc_deepseek';width=4096;height=2**math.ceil(math.log2(math.ceil(cursor/width)));assert height<=4096
    data=np.zeros((width*height,4),np.uint8);data[:cursor]=np.concatenate(blocks)
    Image.fromarray(data.reshape(height,width,4)).save(tex/'poses.png')
    mw=1024;mh=2**math.ceil(math.log2(math.ceil(len(meta)/mw)));mt=np.zeros((mw*mh,4),np.uint8);mt[:len(meta)]=meta
    Image.fromarray(mt.reshape(mh,mw,4)).save(tex/'meta.png')
    (RP/'models/bongocatmc_deepseek/mesh.json').write_text(json.dumps({'mesh':[{'material':'bongocatmc_deepseek/atlas','vertices':vertices,'indices':indices}]},separators=(',',':')))
    constants={'DATA_W':width,'DATA_H':height,'META_H':mh,'DRAW_META':draw_meta,'KEY_META':key_meta,'PARAM_META':param_meta,'KEY_CHANNEL':len(params)}
    (RP/'shaders/glsl/bongocatmc_deepseek_data.h').write_text(''.join('#define %s %.1f\n'%(k,v) for k,v in constants.items()))
    cfg=json.loads((SRC/'deepseek.model3.json').read_text());motions={};expressions={}
    for entry in cfg['FileReferences']['Motions']['CAT_motion_lock']:
        clip=json.loads((SRC/entry['File']).read_text());clip['FadeInTime']=entry.get('FadeInTime',1.);clip['FadeOutTime']=entry.get('FadeOutTime',1.)
        clip['sound']=entry.get('Sound');motions[entry['File'].split('.')[0]]=clip
    for entry in cfg['FileReferences']['Expressions']:expressions[entry['Name']]=json.loads((SRC/entry['File']).read_text())
    physics=json.loads((SRC/'deepseek.physics3.json').read_text(encoding='utf8'))
    text='# -*- coding: utf-8 -*-\n# Generated source parameters and original effect definitions.\n'
    for name,value in [('PARAMETERS',params),('PHYSICS',physics),('MOTIONS',motions),('EXPRESSIONS',expressions),('KEY_ART',{r['name']:i for i,r in enumerate(keys)})]:text+=name+' = '+ascii(value)+'\n'
    (BP/'bongocat_mod/client/deepseek_parameters.py').write_text(text,encoding='utf8')
    print('Runtime data texture',width,height,'texels',cursor,'bytes',sum(p.stat().st_size for p in tex.glob('*.png')))

if __name__=='__main__':build()
