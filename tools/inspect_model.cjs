const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const core = new Function('require', '__dirname', fs.readFileSync(path.join(__dirname, 'vendor/live2dcubismcore.min.js'), 'utf8') + ';return Live2DCubismCore;')(require, path.join(__dirname, 'vendor'));
setTimeout(() => {
  const b = fs.readFileSync(path.join(root, 'assets/source/standard/demomodel.moc3'));
  const moc = core.Moc.fromArrayBuffer(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
  const model = core.Model.fromMoc(moc);
  model.update();
  const p = model.parameters, d = model.drawables;
  console.log(JSON.stringify({canvas:model.canvasinfo, parameters:p.ids.map((id,i)=>({id,min:p.minimumValues[i],max:p.maximumValues[i],value:p.defaultValues[i]})),drawables:d.ids.map((id,i)=>({id,vertices:d.vertexCounts[i],mask:Array.from(d.masks[i]),flags:d.constantFlags[i],order:d.renderOrders[i]}))}, null, 2));
  model.release(); moc._release();
}, 200);
