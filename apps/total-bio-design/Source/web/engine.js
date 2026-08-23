class WorkbookEngine {
  constructor(model) {
    this.model = model;
    this.overrides = {};
    this.cache = {};
    this.active = new Set();
    this.errors = [];
  }
  key(sheet, addr) { return `${sheet}!${String(addr).replace(/\$/g,'').toUpperCase()}`; }
  raw(sheet, addr) {
    addr = String(addr).replace(/\$/g,'').toUpperCase();
    return this.model.sheets?.[sheet]?.cells?.[addr] || null;
  }
  set(sheet, addr, value) {
    this.overrides[this.key(sheet, addr)] = value;
    this.recalculate();
  }
  unset(sheet, addr) {
    delete this.overrides[this.key(sheet, addr)];
    this.recalculate();
  }
  recalculate() { this.cache = {}; this.active.clear(); this.errors = []; }
  get(sheet, addr) {
    const k = this.key(sheet, addr);
    if (Object.prototype.hasOwnProperty.call(this.overrides, k)) return this.overrides[k];
    if (Object.prototype.hasOwnProperty.call(this.cache, k)) return this.cache[k];
    const c = this.raw(sheet, addr);
    if (!c) return 0;
    if (!c.formula) return c.value ?? 0;
    if (this.active.has(k)) {
      this.errors.push(`Circular reference: ${k}`);
      return NaN;
    }
    this.active.add(k);
    let v;
    try { v = this.evaluateFormula(sheet, c.formula); }
    catch (e) {
      this.errors.push(`${k}: ${e.message}`);
      v = NaN;
    }
    this.active.delete(k);
    this.cache[k] = v;
    return v;
  }
  getInputValue(sheet, addr) {
    const k=this.key(sheet,addr);
    return Object.prototype.hasOwnProperty.call(this.overrides,k) ? this.overrides[k] : (this.raw(sheet,addr)?.value ?? '');
  }
  exportInputs() { return {...this.overrides}; }
  importInputs(values) { this.overrides = {...(values || {})}; this.recalculate(); }
  reset() { this.overrides = {}; this.recalculate(); }
  colNum(c) { let n=0; for (const ch of c.toUpperCase()) n=n*26+ch.charCodeAt(0)-64; return n; }
  colName(n) { let s=''; while(n){ const r=(n-1)%26; s=String.fromCharCode(65+r)+s; n=Math.floor((n-1)/26); } return s; }
  parseAddr(a) { const m=String(a).replace(/\$/g,'').match(/^([A-Z]+)(\d+)$/i); if(!m) throw new Error(`Bad cell address ${a}`); return [this.colNum(m[1]), Number(m[2])]; }
  range(sheet, a1, a2) {
    let [c1,r1]=this.parseAddr(a1), [c2,r2]=this.parseAddr(a2), out=[];
    if(c1>c2) [c1,c2]=[c2,c1]; if(r1>r2) [r1,r2]=[r2,r1];
    for(let r=r1;r<=r2;r++){ let row=[]; for(let c=c1;c<=c2;c++) row.push(this.get(sheet,`${this.colName(c)}${r}`)); out.push(row); }
    return out;
  }
  protectStrings(expr) {
    const strings=[]; let out='';
    for(let i=0;i<expr.length;){
      if(expr[i]==='"'){
        let j=i+1, s='"';
        while(j<expr.length){ s+=expr[j]; if(expr[j]==='"' && expr[j-1]!=="\\"){ j++; break; } j++; }
        out += `§${strings.length}§`; strings.push(s); i=j;
      } else out += expr[i++];
    }
    return [out,strings];
  }
  evaluateFormula(sheet, formula) {
    let expr = formula.startsWith('=') ? formula.slice(1) : formula;
    let strings; [expr,strings] = this.protectStrings(expr);
    expr = expr.replace(/([A-Za-z_][A-Za-z0-9_]*)!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)/g,
      (m,s,c1,r1,c2,r2)=>`R("${s}","${c1}${r1}","${c2}${r2}")`);
    expr = expr.replace(/([A-Za-z_][A-Za-z0-9_]*)!\$?([A-Z]+)\$?(\d+)/g,
      (m,s,c,r)=>`C("${s}","${c}${r}")`);
    expr = expr.replace(/(?<![A-Za-z0-9_"'])\$?([A-Z]{1,3})\$?(\d+):\$?([A-Z]{1,3})\$?(\d+)/g,
      (m,c1,r1,c2,r2)=>`R("${sheet}","${c1}${r1}","${c2}${r2}")`);
    expr = expr.replace(/(?<![A-Za-z0-9_"'])\$?([A-Z]{1,3})\$?(\d+)/g,
      (m,c,r)=>`C("${sheet}","${c}${r}")`);
    expr = expr.replace(/\^/g,'**').replace(/(?<![<>=!])=(?!=)/g,'==');
    strings.forEach((s,i)=>{ expr = expr.replaceAll(`§${i}§`,s); });

    const IF=(cond,a,b)=>cond?a:b;
    const MIN=(...args)=>Math.min(...args.flat(Infinity).map(Number));
    const MAX=(...args)=>Math.max(...args.flat(Infinity).map(Number));
    const ABS=x=>Math.abs(Number(x));
    const EXP=x=>Math.exp(Number(x));
    const LN=x=>Math.log(Number(x));
    const SQRT=x=>Math.sqrt(Number(x));
    const PI=()=>Math.PI;
    const AND=(...args)=>args.every(Boolean);
    const LEFT=(x,n)=>String(x??'').slice(0,Number(n));
    const ROUNDUP=(x,d=0)=>{ x=Number(x); d=Number(d); const p=10**d; return x>=0?Math.ceil(x*p)/p:Math.floor(x*p)/p; };
    const INDEX=(arr,row,col=1)=>{ const r=Number(row)-1,c=Number(col)-1; if(!Array.isArray(arr))return arr; if(!Array.isArray(arr[0]))return arr[r]; return arr[r]?.[c]; };
    const MATCH=(lookup,arr,type=1)=>{
      const a=Array.isArray(arr)?arr.flat(Infinity):[arr]; type=Number(type);
      if(type===0){ for(let i=0;i<a.length;i++) if(a[i]===lookup || String(a[i])===String(lookup)) return i+1; return NaN; }
      if(type===1){ let idx=NaN; for(let i=0;i<a.length;i++){ const v=a[i]; if(typeof v==='number'&&typeof lookup==='number'){ if(v<=lookup)idx=i+1; else break; } else { if(String(v)<=String(lookup))idx=i+1; else break; } } return idx; }
      if(type===-1){ let idx=NaN; for(let i=0;i<a.length;i++){ if(a[i]>=lookup)idx=i+1; else break; } return idx; }
      return NaN;
    };
    const fn = new Function('C','R','IF','MIN','MAX','ABS','EXP','LN','SQRT','PI','AND','LEFT','ROUNDUP','INDEX','MATCH',`return (${expr});`);
    return fn((s,a)=>this.get(s,a),(s,a,b)=>this.range(s,a,b),IF,MIN,MAX,ABS,EXP,LN,SQRT,PI,AND,LEFT,ROUNDUP,INDEX,MATCH);
  }
}
if(typeof window!=='undefined') window.WorkbookEngine=WorkbookEngine;
if(typeof module!=='undefined' && module.exports) module.exports=WorkbookEngine;
