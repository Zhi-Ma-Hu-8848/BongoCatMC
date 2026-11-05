// Build-time Cubism evaluation. Runtime uses original meshes, not image frames.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
fs.mkdirSync(path.join(root, 'build'), {recursive:true});
const source = path.join(root, 'assets/source/standard');
const core = new Function('require', '__dirname', fs.readFileSync(path.join(__dirname, 'vendor/live2dcubismcore.min.js'), 'utf8') + ';return Live2DCubismCore;')(require, path.join(__dirname, 'vendor'));
setTimeout(() => {
  const b=fs.readFileSync(path.join(source,'demomodel.moc3'));
  const moc=core.Moc.fromArrayBuffer(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));
  if(!moc) throw Error('Invalid default cat MOC');
  const model=core.Model.fromMoc(moc), d=model.drawables, p=model.parameters;
  const defaults=Array.from(p.defaultValues), set=(id,value)=>{const i=p.ids.indexOf(id);if(i<0)throw Error(id);p.values[i]=value;};
  const vertexCount=Array.from(d.vertexCounts).reduce((a,b)=>a+b,0), stride=vertexCount*2+d.count*2;
  const data=[], records=[];
  for(let eye=0;eye<2;eye++)for(let key=0;key<2;key++)for(let left=0;left<2;left++)for(let right=0;right<2;right++)for(let y=0;y<5;y++)for(let x=0;x<5;x++){
    p.values.set(defaults);
    set('ParamAngleX',(x-2)*15);set('ParamAngleY',(y-2)*15);
    set('ParamMouseX',(x-2)*15);set('ParamMouseY',(y-2)*15);
    set('ParamEyeLOpen',1-eye);set('ParamEyeROpen',1-eye);
    set('CatParamLeftHandDown',key);set('ParamMouseLeftDown',left);set('ParamMouseRightDown',right);
    model.update();
    for(let i=0;i<d.count;i++)data.push(...d.vertexPositions[i]);
    data.push(...d.opacities,...d.renderOrders);
    records.push({x,y,eye,key,left,right});
  }
  const drawables=d.ids.map((id,i)=>({id,texture:d.textureIndices[i],flags:d.constantFlags[i],uvs:Array.from(d.vertexUvs[i]),indices:Array.from(d.indices[i]),masks:Array.from(d.masks[i]),vertexCount:d.vertexCounts[i]}));
  const output=new Float32Array(data);
  fs.writeFileSync(path.join(root,'build/poses.f32'),Buffer.from(output.buffer));
  fs.writeFileSync(path.join(root,'build/model.json'),JSON.stringify({canvas:model.canvasinfo,vertexCount,stride,poseCount:records.length,drawables,records}));
  console.log(JSON.stringify({vertices:vertexCount,drawables:d.count,poses:records.length,bytes:output.byteLength}));
  model.release();moc._release();
},200);
