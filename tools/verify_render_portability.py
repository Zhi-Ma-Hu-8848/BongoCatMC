"""Render real meshes/textures in GLSL/ESSL and compare with desktop output.

This uses the desktop GPU compiler, not an Android/iOS device. Numeric texture
and shader paths are exercised with real art, masks, expressions and input.
"""
import argparse
import json
import re
import sys
from pathlib import Path
import moderngl
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT/'addon/resource_pack'
sys.path.insert(0,str(ROOT/'addon/behavior_pack'))
from bongocat_mod.client.data import KEY_ART
from bongocat_mod.client.deepseek_effects import DeepseekEffects


def expand(path, roots):
    def include(match):
        for root in roots:
            source = root/match[1]
            if source.is_file():
                return expand(source,roots)
        raise FileNotFoundError(match[1])
    return re.sub(r'#include\s+"([^\"]+)"',include,path.read_text(encoding='utf-8-sig'))


def samples(model):
    if model == 'default':
        for name,head,clicks,effects in [
                ('idle',(2,2,0,0),(0,0,0,0),(0,0,0,0)),
                ('blink_mouse',(4,0,1,0),(1,1,0,0),(0,0,0,0)),
                ('key',(0,4,0,1),(0,0,KEY_ART['KeyW'],0),(0,0,0,0)),
                ('glasses',(3,1,0,0),(0,0,0,0),(.5,0,0,0)),
                ('halo',(1,3,0,0),(0,0,0,0),(0,1,0,0)),
                ('wave',(4,4,0,0),(0,0,0,0),(0,0,18,0)),
                ('flash',(0,0,0,0),(0,0,0,1),(0,0,0,.5))]:
            yield name,[head,clicks,(1.,0.,0.,0.),effects]
    else:
        for i,name in enumerate(('idle','key','Bowl','Glasses','StickyNotes','Egg',
                                  'Surprised','Hello','Sweat','Heart','combined')):
            fx=DeepseekEffects();fx.random.seed(0);fx.blink_next=2.
            if name in ('Bowl','Glasses','StickyNotes','Egg'):fx.select(name,0.)
            if name in ('Surprised','Hello','Sweat','Heart'):fx.play(name,0.)
            if name=='combined':
                fx.select('Glasses',0.);fx.play('Heart',0.);fx.play('Sweat',0.)
            state={'key':name in ('key','combined'),'art':'KeyW',
                   'left':i%2==1,'right':i%3==1}
            for frame in range(73):fx.frame(frame/60.,[(i%3-1)*.8,((i//3)%3-1)*.7],state)
            yield name,fx.packed((1.,0.,0.,float(i%4)),state)


def render(ctx, folder, headers, version, model, vectors, mesh, textures):
    name='bongocatmc' if model=='default' else 'bongocatmc_deepseek'
    roots=[folder]+headers
    prefix='#version '+version+'\n#define POS4 vec4\n#define MAT4 mat4\n'
    if version.endswith('es'):prefix+='precision highp float;\nprecision highp int;\n'
    if version=='120':prefix+='#define highp\n#define mediump\n#define lowp\n'
    program=ctx.program(vertex_shader=prefix+expand(folder/(name+'.vertex'),roots),
                        fragment_shader=prefix+expand(folder/(name+'.fragment'),roots))
    for i,texture in enumerate(textures):
        texture.use(i);program['TEXTURE_'+str(i)].value=i
    for i,vector in enumerate(vectors,1):program['EXTRA_VECTOR'+str(i)].value=vector
    matrix=np.eye(4,dtype=np.float32);matrix[0,0]=matrix[1,1]=1/24.;matrix[1,3]=-16/24.
    program['WORLDVIEWPROJ'].write(matrix.T.tobytes())
    uv=ctx.buffer(np.array([v['uvcoord'] for v in mesh['vertices']],np.float32).tobytes())
    indices=ctx.buffer(np.array(mesh['indices'],np.uint32).tobytes())
    vao=ctx.vertex_array(program,[(uv,'2f','TEXCOORD_0')],indices)
    target=ctx.simple_framebuffer((512,512),components=4)
    target.use();ctx.viewport=(0,0,512,512);target.clear(0,0,0,0)
    ctx.enable(moderngl.BLEND);ctx.disable(moderngl.DEPTH_TEST|moderngl.CULL_FACE)
    ctx.blend_func=moderngl.ONE,moderngl.ONE_MINUS_SRC_ALPHA
    vao.render(moderngl.TRIANGLES)
    pixels=np.frombuffer(target.read(components=4,alignment=1),np.uint8).reshape(512,512,4).copy()
    target.release();vao.release();uv.release();indices.release();program.release()
    return pixels


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers',action='append',type=Path,required=True)
    parser.add_argument('--baseline-shaders',type=Path)
    args=parser.parse_args();ctx=moderngl.create_standalone_context(require=330)
    folder=RP/'shaders/glsl';out=ROOT/'diagnostics/mobile-shaders';out.mkdir(parents=True,exist_ok=True)
    registry=json.loads((RP/'models/netease_models.json').read_text());results=[]
    for model in ('default','deepseek'):
        entry=registry['bongocatmc_'+model]
        mesh=json.loads((RP/'models'/entry['mesh']).read_text())['mesh'][0]
        textures=[]
        for i in range(3):
            with Image.open(RP/'textures/models'/(entry['texture']['tex'+str(i)]+'.png')) as im:
                im=im.convert('RGBA');texture=ctx.texture(im.size,4,im.tobytes())
            texture.filter=(moderngl.LINEAR,moderngl.LINEAR) if i==0 else (moderngl.NEAREST,moderngl.NEAREST)
            texture.repeat_x=texture.repeat_y=False;textures.append(texture)
        for name,vectors in samples(model):
            reference=render(ctx,args.baseline_shaders or folder,args.headers,'330 core',model,vectors,mesh,textures)
            assert np.count_nonzero(reference[:,:,3])>1000, 'Empty reference render: '+model+'/'+name
            for version in ('120','330 core','300 es','310 es'):
                pixels=render(ctx,folder,args.headers,version,model,vectors,mesh,textures)
                error=np.abs(pixels.astype(int)-reference.astype(int))
                results.append(dict(model=model,sample=name,version=version,max_channel_error=int(error.max()),
                                    mean_channel_error=float(error.mean()),visible_pixels=int(np.count_nonzero(pixels[:,:,3]))))
                assert error.max()<=2 and error.mean()<.01, results[-1]
            Image.fromarray(pixels[::-1]).save(out/(model+'_'+name+'.png'))
        for texture in textures:texture.release()
    (out/'pixels.json').write_text(json.dumps(dict(renderer=ctx.info['GL_RENDERER'],results=results,
        limitation='Desktop driver, not phone runtime; real mesh/art and fixed input samples.'),indent=2))
    print('Passed %d real-mesh comparisons; max channel error %d' % (len(results),max(r['max_channel_error'] for r in results)))
    ctx.release()


if __name__=='__main__':main()
