"""Build native-resolution DeepSeek art, then continuous parameter data.

Run node tools/sample_deepseek_parameters.cjs first. Never emits legacy
whole-animation pose banks: mesh, shader metadata and data stay paired.
"""
import json, math
import numpy as np
from PIL import Image
from build_cat import ROOT, RP, save, premultiply_rgba

SRC=ROOT/'assets/source/deepseek/img/standard/cat_model'

def build_art():
    model=json.loads((ROOT/'build/deepseek_parameters/model.json').read_text())
    ds=model['drawables'];n=sum(d['vertexCount'] for d in ds)
    # Reserve every source UV bounding rectangle, including transparent pixels
    # sampled by a drawable. Key art may use only untouched atlas space.
    atlas=Image.open(SRC/'deepseek.4096/texture_00.png').convert('RGBA')
    assert atlas.size==(4096,4096)
    occupied=np.zeros((1024,1024),bool)
    for d in ds:
        uv=np.array(d['uvs']).reshape(-1,2); uv[:,1]=1-uv[:,1]
        lo=np.maximum(0,np.floor(uv.min(axis=0)*1024-2).astype(int));hi=np.minimum(1024,np.ceil(uv.max(axis=0)*1024+2).astype(int))
        occupied[lo[1]:hi[1],lo[0]:hi[0]]=True
    keys=sorted((SRC/'resources/left-keys').glob('*.png')); records=[]
    for path in keys:
        im=Image.open(path).convert('RGBA');assert im.size==(1024,1024)
        box=im.getchannel('A').getbbox();crop=im.crop(box);w,h=crop.size
        cw,ch=math.ceil((w+8)/4),math.ceil((h+8)/4)
        found=None
        for y in range(0,1024-ch,2):
            for x in range(0,1024-cw,2):
                if not occupied[y:y+ch,x:x+cw].any():found=(x,y);break
            if found:break
        if found is None:raise ValueError('No untouched atlas area for native hand art')
        x,y=found;occupied[y:y+ch,x:x+cw]=True;origin=(x*4+4,y*4+4)
        atlas.paste(crop,origin);records.append({'name':path.stem,'origin':origin,'box':box,'size':(w,h)})
    tex=RP/'textures/models/bongocatmc_deepseek';tex.mkdir(parents=True,exist_ok=True)
    premultiply_rgba(atlas).save(tex/'atlas.png')
    out=RP/'models/bongocatmc_deepseek';out.mkdir(parents=True,exist_ok=True)
    skeleton=json.loads((RP/'models/bongocatmc/cat_skeleton.json').read_text());save(out/'skeleton.json',skeleton)
    registry=RP/'models/netease_models.json';models=json.loads(registry.read_text())
    models['bongocatmc_deepseek']={'dy_load':True,'mesh':'bongocatmc_deepseek/mesh.json','skeleton':'bongocatmc_deepseek/skeleton.json','animation':{},'material':'bongocatmc_deepseek','texture':{'tex0':'bongocatmc_deepseek/atlas','tex1':'bongocatmc_deepseek/poses','tex2':'bongocatmc_deepseek/meta'}};save(registry,models)
    materials=RP/'materials/entity.material';data=json.loads(materials.read_text());mat=dict(data['materials']['bongocatmc_mesh:entity_for_skeleton'])
    mat.update(vertexShader='shaders/glsl/bongocatmc_deepseek.vertex',fragmentShader='shaders/glsl/bongocatmc_deepseek.fragment')
    data['materials']['bongocatmc_deepseek:entity_for_skeleton']=mat;save(materials,data)
    import soundfile as sf
    audio=RP/'sounds/bongocatmc';sounds_path=RP/'sounds/sound_definitions.json';sounds=json.loads(sounds_path.read_text())
    cfg=json.loads((SRC/'deepseek.model3.json').read_text())
    for clip in cfg['FileReferences']['Motions']['CAT_motion_lock']:
        if clip.get('Sound'):
            samples,rate=sf.read(SRC/clip['Sound'],dtype='int16');name='deepseek_'+clip['File'].split('.')[0].lower()
            sf.write(audio/(name+'.wav'),samples,rate,subtype='PCM_16')
            sounds['bongocatmc.'+name]={'category':'ui','sounds':[{'name':'sounds/bongocatmc/'+name,'stream':False}]}
    save(sounds_path,sounds)
    save(ROOT/'tools/fixtures/deepseek_keys.json',records)
    save(ROOT/'diagnostics/deepseek_build.json',{'vertices':n,'atlas_size':[4096,4096],'key_source_scale':1,'keys':records})

if __name__=='__main__':
    build_art()
    from build_deepseek_parameters import build
    build()
