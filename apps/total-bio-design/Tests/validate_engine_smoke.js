const fs = require('fs');
const path = require('path');
const web = path.join(__dirname, '..', 'Source', 'web');
const WorkbookEngine = require(path.join(web, 'engine.js'));
const model = JSON.parse(fs.readFileSync(path.join(web, 'model.json'), 'utf8'));
const engine = new WorkbookEngine(model);
for (const addr of ['C28', 'C38', 'C40']) {
  const value = Number(engine.get('Summary', addr));
  if (!Number.isFinite(value)) throw new Error(`Summary!${addr} is not finite: ${value}`);
}
const network = require(path.join(web, 'process_network.js'));
const influent = network.makeStream(1000, {cod:300,bod:180,tss:220,vss:170,tkn:40,nh4:25,nox:0,tp:7,po4:4,fog:10,alk:180}, {temperatureC:20,pH:7,label:'Smoke influent'});
const solved = network.solveIntegratedNetwork({influent,units:[],recycles:[],sludgeLines:[]}, {maxIterations:400,maxOuterIterations:35,tolerance:1e-5,outerTolerance:1e-4,relaxation:0.8});
if (!solved || !solved.water || Math.abs(solved.water.finalEffluent.flow - 1000) > 1e-9) throw new Error('Process-network smoke mass balance failed');
console.log('Bio workbook engine and process-network smoke: PASS');
