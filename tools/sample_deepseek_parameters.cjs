// Compile separable local deformations and their parent affine transforms.
// Core is used only at build time; runtime evaluates continuous parameters.
const fs=require('fs'),path=require('path');
const dir='assets/source/deepseek/img/standard/cat_model',out='build/deepseek_parameters';
fs.mkdirSync(out,{recursive:true});
const core=new Function('require','__dirname',fs.readFileSync('tools/vendor/live2dcubismcore-deepseek.min.js','utf8')+';return Live2DCubismCore;')(require,path.resolve('tools/vendor'));
setTimeout(()=>{try{
 const b=fs.readFileSync(dir+'/deepseek.moc3'),m=core.Model.fromMoc(core.Moc.fromArrayBuffer(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength))),p=m.parameters,d=m.drawables;
 const omitted=['ParamBrowLY','ParamBrowRY','ParamMouthForm','ParamMouthOpenY','ParamBodyAngleY','ParamBodyAngleZ'];
 const active=p.ids.filter(id=>!omitted.includes(id)),defaults=Array.from(p.defaultValues);
 const outer=['ParamAngleZ','ParamBodyAngleX','ParamBreath'];
 const clothes=['ArtMeshNeckwear','ArtMeshTopwear','ArtMeshLegwearL','ArtMeshLegwearR'];
 const params=active.map(id=>{let i=p.ids.indexOf(id);return {id,min:p.minimumValues[i],max:p.maximumValues[i],default:p.defaultValues[i]};});
 function set(id,v){p.values[p.ids.indexOf(id)]=v;}
 function reset(){p.values.set(defaults);}
 reset();m.update();const base=d.vertexPositions.map(x=>Array.from(x)),baseop=Array.from(d.opacities);
 const pd=d.ids.map(()=>[]),od=d.ids.map(()=>[]);
 for(const q of params)for(const v of [q.min,q.max,(q.min+q.max)*.5]){
  reset();set(q.id,v);m.update();for(let di=0;di<d.count;di++){
   if(d.vertexPositions[di].some((x,j)=>Math.abs(x-base[di][j])>1e-6)&&!pd[di].includes(q.id))pd[di].push(q.id);
   if(Math.abs(d.opacities[di]-baseop[di])>1e-6&&!od[di].includes(q.id))od[di].push(q.id);
  }
 }
 const drawables=d.ids.map((id,i)=>({id,vertexCount:d.vertexCounts[i],uvs:Array.from(d.vertexUvs[i]),indices:Array.from(d.indices[i]),masks:Array.from(d.masks[i]),flags:d.constantFlags[i],order:m.renderOrders[i],base:base[i],outer:!clothes.includes(id),positionParams:pd[i],opacityParams:od[i]}));
 const records=[],file=fs.openSync(out+'/samples.f32','w');let floatOffset=0;
 function count(id){
  if(['ParamAngleX','ParamAngleZ'].includes(id))return 13;
  if(['ParamAngleY','ParamBodyAngleX','ParamMouseX','ParamMouseY'].includes(id))return 9;
  if(id.startsWith('Param_Angle_'))return 13;
  if(['Hearting','Sweat','MouthOpen'].includes(id))return 31;
  if(id==='Hello')return 25;
  if(id.includes('Eye')||id.includes('Hair')||id.includes('Ear')||id.includes('Ahoge'))return 9;
  return ['ParamBreath','Bowl','Glasses','StickyNotes','SargonTea','MostimaCat','SkillReady'].includes(id)?5:2;
 }
 function sample(di,kind,ids){
  if(ids.length>4)throw Error(kind+' has too many local parameters: '+d.ids[di]+' '+ids);
  const counts=ids.map(count),num=counts.reduce((a,b)=>a*b,1),nv=d.vertexCounts[di],mask=drawables[di].masks[0];
  const stride=kind==='opacity'?2:kind==='mask'?(nv+d.vertexCounts[mask])*2:nv*2;
  const data=new Float32Array(num*stride);
  for(let f=0;f<num;f++){
   reset();let at=f;for(let axis=0;axis<ids.length;axis++){
    const q=params[active.indexOf(ids[axis])],v=at%counts[axis];at=Math.floor(at/counts[axis]);set(q.id,q.min+(q.max-q.min)*v/(counts[axis]-1));
   }m.update();const dest=f*stride;
   if(kind==='opacity')data[dest]=d.opacities[di];
   else{data.set(d.vertexPositions[di],dest);if(kind==='mask')data.set(d.vertexPositions[mask],dest+nv*2);}
  }
  records.push({di,kind,dims:ids.map(id=>active.indexOf(id)),counts,floatOffset,stride,num});
  fs.writeSync(file,Buffer.from(data.buffer));floatOffset+=data.length;
 }
 for(let di=0;di<d.count;di++){
  const obj=drawables[di],local=pd[di].filter(id=>!obj.outer||!outer.includes(id));
  sample(di,'position',local);sample(di,'opacity',od[di]);
  sample(di,'outer',obj.outer?pd[di].filter(id=>outer.includes(id)):[]);
  if(obj.masks.length){
   const mask=obj.masks[0],ids=Array.from(new Set([...local,...pd[mask].filter(id=>!drawables[mask].outer||!outer.includes(id))]));
   sample(di,'mask',ids);
  }
  if(di%10===0)console.log('sampled part',di,d.ids[di]);
 }
 fs.closeSync(file);
 // Independent combinations used to bound interpolation and decomposition errors.
 let seed=209;function rand(){seed=(Math.imul(1664525,seed)+1013904223)>>>0;return seed/4294967296;}
 const checks=[],vf=fs.openSync(out+'/validation.f32','w');
 for(let k=0;k<100;k++){
  reset();let values=params.map(q=>q.min+rand()*(q.max-q.min));values.forEach((v,i)=>set(active[i],v));m.update();
  const a=[];for(let di=0;di<d.count;di++)a.push(...d.vertexPositions[di]);a.push(...d.opacities);fs.writeSync(vf,Buffer.from(new Float32Array(a).buffer));checks.push(values);
 }fs.closeSync(vf);
 fs.writeFileSync(out+'/model.json',JSON.stringify({params,drawables,records,checks,baseop}));
 console.log('Done:',params.length,'parameters,',floatOffset*4,'sample bytes');m.release();
}catch(e){console.error(e.message,e.stack?.split('\n').slice(-5).join('\n'));process.exitCode=1;}},200);
