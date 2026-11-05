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
  const banks={};
  const groups={glasses:['ArtMesh18','ArtMesh19','ArtMesh23'],halo:['ArtMesh21','ArtMesh22'],wave:['rightgand'],flash:['ArtMesh11','ArtMesh14','ArtMesh15','ArtMesh16']};
  // A stationary drawable can still animate when its clipping mask moves
  // (the glasses' smoke is clipped by ArtMesh23).
  for(const group of Object.values(groups)){
    for(let pass=0;pass<d.count;pass++)for(let i=0;i<d.count;i++){
      if(!group.includes(d.ids[i]) && Array.from(d.masks[i]).some(mask=>group.includes(d.ids[mask])))group.push(d.ids[i]);
    }
  }
  for(const [name,id,count,max,visibility] of [['glasses','Param4',101,1,null],['halo','Param5',11,1,null],['wave','Param3',31,30,null],['flash0','Param2',31,1,0],['flash','Param2',31,1,1]]){
    banks[name]={start:records.length,count};
    for(let level=0;level<count;level++)for(let y=0;y<5;y++)for(let x=0;x<5;x++){
      p.values.set(defaults);
      set('ParamAngleX',(x-2)*15);set('ParamAngleY',(y-2)*15);
      set('ParamMouseX',(x-2)*15);set('ParamMouseY',(y-2)*15);
      set(id,max*level/(count-1));if(visibility!==null)set('Param',visibility);
      model.update();
      for(let i=0;i<d.count;i++)data.push(...d.vertexPositions[i]);
      data.push(...d.opacities,...d.renderOrders);records.push({name,level,x,y});
    }
  }
  // Validate parameter independence against Core, including concurrent input.
  let maxError=0;
  for(let test=0;test<80;test++){
    const x=test%5,y=Math.floor(test/5)%5,level=test%11,wave=test%31;
    p.values.set(defaults);
    for(const id of ['ParamAngleX','ParamMouseX'])set(id,(x-2)*15);
    for(const id of ['ParamAngleY','ParamMouseY'])set(id,(y-2)*15);
    set('Param4',level/10);set('Param5',level/10);set('Param3',wave);
    set('Param',test%2);set('Param2',wave/30);
    set('ParamEyeLOpen',test%2);set('ParamEyeROpen',test%2);
    set('ParamMouseLeftDown',test%2);set('ParamMouseRightDown',Math.floor(test/2)%2);
    model.update();let offset=0;
    for(let di=0;di<d.count;di++){
      const group=Object.keys(groups).find(g=>groups[g].includes(d.ids[di]));
      if(group){const bank=banks[group==='flash' && test%2===0?'flash0':group];const lev=['glasses','halo'].includes(group)?level/10*(bank.count-1):wave;const frame=bank.start+25*lev+y*5+x;
        for(let j=0;j<d.vertexPositions[di].length;j++)maxError=Math.max(maxError,Math.abs(d.vertexPositions[di][j]-data[frame*stride+offset+j]));
        maxError=Math.max(maxError,Math.abs(d.opacities[di]-data[frame*stride+vertexCount*2+di]));
      }offset+=d.vertexCounts[di]*2;
    }
  }
  if(maxError>1e-5)throw Error('Effect banks are not independent: '+maxError);
  console.log('Concurrent effects Core validation max error: '+maxError);
  // Check interpolation between parameter samples, not only sampled endpoints.
  let interpolationError=0;const interpolationByGroup={};
  for(let test=0;test<40;test++){
    const x=test%5,y=Math.floor(test/5)%5,v=(test+.31)/40;
    p.values.set(defaults);
    for(const id of ['ParamAngleX','ParamMouseX'])set(id,(x-2)*15);
    for(const id of ['ParamAngleY','ParamMouseY'])set(id,(y-2)*15);
    set('Param4',v);set('Param5',v);set('Param3',30*v);set('Param',v);set('Param2',v);
    model.update();let offset=0;
    function interpolated(name,index){const b=banks[name],level=v*(b.count-1),lo=Math.floor(level),hi=Math.ceil(level),t=level-lo;return data[(b.start+25*lo+y*5+x)*stride+index]*(1-t)+data[(b.start+25*hi+y*5+x)*stride+index]*t;}
    for(let di=0;di<d.count;di++){
      const group=Object.keys(groups).find(g=>groups[g].includes(d.ids[di]));
      if(group){interpolationByGroup[group]=interpolationByGroup[group]||0;const read=index=>group==='flash'?interpolated('flash0',index)*(1-v)+interpolated('flash',index)*v:interpolated(group,index);
        for(let j=0;j<d.vertexPositions[di].length;j++){const err=Math.abs(d.vertexPositions[di][j]-read(offset+j));interpolationError=Math.max(interpolationError,err);interpolationByGroup[group]=Math.max(interpolationByGroup[group],err);}
        interpolationError=Math.max(interpolationError,Math.abs(d.opacities[di]-read(vertexCount*2+di)));
      }offset+=d.vertexCounts[di]*2;
    }
  }
  console.log('Effect interpolation max error: '+interpolationError);
  console.log(interpolationByGroup);if(interpolationError>.003)process.exit(1);
  const drawables=d.ids.map((id,i)=>({id,effect:1+Object.keys(groups).findIndex(g=>groups[g].includes(id)),texture:d.textureIndices[i],flags:d.constantFlags[i],uvs:Array.from(d.vertexUvs[i]),indices:Array.from(d.indices[i]),masks:Array.from(d.masks[i]),vertexCount:d.vertexCounts[i]}));
  const output=new Float32Array(data);
  fs.writeFileSync(path.join(root,'build/poses.f32'),Buffer.from(output.buffer));
  fs.writeFileSync(path.join(root,'build/model.json'),JSON.stringify({canvas:model.canvasinfo,vertexCount,stride,poseCount:records.length,drawables,records,banks}));
  console.log(JSON.stringify({vertices:vertexCount,drawables:d.count,poses:records.length,bytes:output.byteLength}));
  model.release();moc._release();
},200);
