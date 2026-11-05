// Cubism evaluation produces vertex numbers, never rendered image frames.
import fs from 'node:fs';
import path from 'node:path';
import {CubismFramework} from './vendor/framework/src/live2dcubismframework';
import {CubismMoc} from './vendor/framework/src/model/cubismmoc';
import {CubismPhysics} from './vendor/framework/src/physics/cubismphysics';
import {CubismMotion} from './vendor/framework/src/motion/cubismmotion';
import {CubismMotionQueueEntry} from './vendor/framework/src/motion/cubismmotionqueueentry';
import {csmVector} from './vendor/framework/src/type/csmvector';
const source=path.resolve('assets/source/deepseek/img/standard/cat_model');
const folder='build/deepseek';fs.mkdirSync(folder,{recursive:true});
const read=(name:string)=>{const b=fs.readFileSync(path.join(source,name));return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);};
(globalThis as any).Live2DCubismCore=new Function('require','__dirname',fs.readFileSync('tools/vendor/live2dcubismcore-deepseek.min.js','utf8')+';return Live2DCubismCore;')(require,path.resolve('tools/vendor'));
async function main(){
 await new Promise(r=>setTimeout(r,200));CubismFramework.startUp();CubismFramework.initialize(128*1024*1024);
 const cfg=JSON.parse(fs.readFileSync(path.join(source,'deepseek.model3.json'),'utf8')).FileReferences;
 const moc=CubismMoc.create(read(cfg.Moc),true);if(!moc)throw Error('Invalid DeepSeek MOC');
 const model=moc.createModel(),core:any=model.getModel(),d=core.drawables;
 const physicsData=read(cfg.Physics),physics=()=>CubismPhysics.create(physicsData,physicsData.byteLength);
 const defaults=new Float32Array(core.parameters.defaultValues);
 const set=(id:string,value:number)=>model.setParameterValueById(CubismFramework.getIdManager().getId(id),value);
 const reset=()=>core.parameters.values.set(defaults);
 const n=Array.from(d.vertexCounts).reduce((a:number,b:number)=>a+b,0),stride=n*2+d.count*2;
 const file=fs.openSync(folder+'/poses.f32','w');let frame=0;
 const capture=()=>{model.update();const out=new Float32Array(stride);let offset=0;
  for(let i=0;i<d.count;i++){out.set(d.vertexPositions[i],offset);offset+=d.vertexPositions[i].length;}
  out.set(d.opacities,offset);out.set(core.renderOrders,offset+d.count);fs.writeSync(file,Buffer.from(out.buffer));frame++;
 };
 const head=(x:number,y:number)=>{set('ParamAngleX',(x-2)*15);set('ParamAngleY',(y-2)*15);set('ParamMouseX',(x-2)*15);set('ParamMouseY',(y-2)*15);};
 // Same input layout as the default cat; physical model settles for each pose.
 for(let eye=0;eye<2;eye++)for(let key=0;key<2;key++)for(let left=0;left<2;left++)for(let right=0;right<2;right++)for(let y=0;y<5;y++)for(let x=0;x<5;x++){
  reset();head(x,y);set('ParamEyeLOpen',1-eye);set('ParamEyeROpen',1-eye);
  set('CatParamLeftHandDown',key);set('ParamMouseLeftDown',left);set('ParamMouseRightDown',right);
  physics().stabilization(model);capture();
 }
 const expressions=[];
 for(const entry of cfg.Expressions){
  const exp=JSON.parse(fs.readFileSync(path.join(source,entry.File),'utf8')),start=frame;
  for(let y=0;y<5;y++)for(let x=0;x<5;x++){
   reset();head(x,y);
   for(const p of exp.Parameters){const id=CubismFramework.getIdManager().getId(p.Id);
    if(p.Blend==='Multiply')model.multiplyParameterValueById(id,p.Value);
    else if(p.Blend==='Overwrite')model.setParameterValueById(id,p.Value);
    else model.addParameterValueById(id,p.Value);
   }physics().stabilization(model);capture();
  }expressions.push({name:entry.Name,start,fadeIn:exp.FadeInTime||1,fadeOut:exp.FadeOutTime||1});
 }
 const motions=[];
 for(const entry of cfg.Motions.CAT_motion_lock){
  const data=read(entry.File),json=JSON.parse(Buffer.from(data).toString('utf8'));
  const motion=CubismMotion.create(data,data.byteLength),queue=new CubismMotionQueueEntry();queue.setStartTime(0);queue.setFadeInStartTime(0);
  motion.setEffectIds(new csmVector(),new csmVector());
  const sim=physics(),duration=json.Meta.Duration,fps=30,steps=Math.ceil(duration*fps),start=frame;
  reset();sim.stabilization(model);
  for(let i=0;i<=steps;i++){reset();motion.doUpdateParameters(model,Math.min(duration,i/fps),1,queue);sim.evaluate(model,1/fps);capture();}
  motions.push({name:entry.File.split('.')[0],start,count:steps+1,duration,fps,sound:entry.Sound||null});
 }
 fs.closeSync(file);
 const drawables=d.ids.map((id:string,i:number)=>({id,texture:d.textureIndices[i],flags:d.constantFlags[i],uvs:Array.from(d.vertexUvs[i]),indices:Array.from(d.indices[i]),masks:Array.from(d.masks[i]),vertexCount:d.vertexCounts[i]}));
 fs.writeFileSync(folder+'/model.json',JSON.stringify({canvas:core.canvasinfo,vertexCount:n,stride,poseCount:frame,drawables,expressions,motions}));
 console.log(JSON.stringify({vertices:n,drawables:d.count,poses:frame,expressions,motions}));
 model.release();
}
main().catch(e=>{console.error(e.message,e.stack?.split('\n').slice(-5).join('\n'));process.exit(1);});
