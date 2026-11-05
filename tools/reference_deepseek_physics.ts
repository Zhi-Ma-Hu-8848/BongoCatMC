import fs from 'node:fs';import path from 'node:path';
import {CubismFramework} from './vendor/framework/src/live2dcubismframework';
import {CubismMoc} from './vendor/framework/src/model/cubismmoc';
import {CubismPhysics} from './vendor/framework/src/physics/cubismphysics';
const root='assets/source/deepseek/img/standard/cat_model';
const read=(f:string)=>{const b=fs.readFileSync(root+'/'+f);return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);};
(globalThis as any).Live2DCubismCore=new Function('require','__dirname',fs.readFileSync('tools/vendor/live2dcubismcore-deepseek.min.js','utf8')+';return Live2DCubismCore;')(require,path.resolve('tools/vendor'));
setTimeout(()=>{
 CubismFramework.startUp();CubismFramework.initialize();const moc=CubismMoc.create(read('deepseek.moc3'),true),model=moc.createModel(),p=model.getModel().parameters;
 const json=read('deepseek.physics3.json'),physics=CubismPhysics.create(json,json.byteLength),defs=Array.from(p.defaultValues);
 const spec=JSON.parse(Buffer.from(json).toString('utf8')),outputs=spec.PhysicsSettings.flatMap((s:any)=>s.Output.map((o:any)=>o.Destination.Id));
 const records=[];let clock=0;
 for(let i=0;i<360;i++){
  const dt=[1/60,1/120,1/30,1/75,.04][i%5];clock+=dt;p.values.set(defs);
  const inputs={ParamAngleX:42*Math.sin(clock*2.4),ParamAngleY:24*Math.sin(clock*1.7),ParamAngleZ:24*Math.sin(clock*1.2),
   ParamBodyAngleX:8*Math.sin(clock*.7),ParamEyeLOpen:clock%2<.15?0:1,ParamEyeROpen:clock%2<.15?0:1,ParamBreath:.5+.5*Math.sin(clock*1.9)};
  for(const [key,value] of Object.entries(inputs))p.values[p.ids.indexOf(key)]=value;
  physics.evaluate(model,dt);records.push({dt,inputs,outputs:Object.fromEntries(outputs.map((id:string)=>[id,p.values[p.ids.indexOf(id)]]))});
 }
 fs.mkdirSync('tools/fixtures',{recursive:true});fs.writeFileSync('tools/fixtures/deepseek_physics_reference.json',JSON.stringify(records));console.log('Saved',records.length,'reference frames');
},200);
