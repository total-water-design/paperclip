import hashlib, json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=os.environ['TWDS_MANAGED_URL']; OUT=Path('deliverables/tot-1885'); SHOTS=OUT/'screenshots'
ROUTES=['/','/platform','/applications','/applications/ro','/applications/pretreatment','/applications/bio','/applications/zld','/applications/balance','/applications/economics','/applications/system_integration']
WIDTHS=[1440,1280,1024,768,390]; SCHEMES=['light','dark']
JS=r'''() => { const cv=c=>{let x=document.createElement('canvas').getContext('2d');x.fillStyle=c;return x.fillStyle}; const rgb=c=>{let m=c.match(/[\d.]+/g).slice(0,3).map(Number);return c.startsWith('color(srgb')?m.map(x=>x*255):m}; const lum=a=>{a=a.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return .2126*a[0]+.7152*a[1]+.0722*a[2]}; const bg=e=>{while(e){let s=getComputedStyle(e);if(s.backgroundImage!='none')return 'rgb(0,76,96)';let c=s.backgroundColor;if(c && !c.endsWith(', 0)') && c!='transparent')return c;e=e.parentElement}return 'rgb(255,255,255)'}; let samples=[]; for(const e of document.querySelectorAll('body *')){let t=[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ');if(!t||!e.getClientRects().length)continue;let s=getComputedStyle(e),f=parseFloat(s.fontSize),w=parseInt(s.fontWeight)||400;if(f>=24||(f>=18.66&&w>=700))continue;let fg=s.color,b=bg(e),r=(Math.max(lum(rgb(fg)),lum(rgb(b)))+.05)/(Math.min(lum(rgb(fg)),lum(rgb(b)))+.05);samples.push({tag:e.tagName,text:t.slice(0,120),foreground:fg,background:b,ratio:r})} return {theme:document.documentElement.dataset.theme||null,colorScheme:getComputedStyle(document.documentElement).colorScheme,overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,samples,contrastFailures:samples.filter(x=>x.ratio<4.5)} }'''
report={'baseUrl':BASE,'workspaceId':os.environ['TWDS_WORKSPACE_ID'],'serviceId':os.environ['TWDS_SERVICE_ID'],'startOperationId':os.environ['TWDS_OPERATION_ID'],'paperclipRunId':os.environ['PAPERCLIP_RUN_ID'],'routes':ROUTES,'widths':WIDTHS,'osPreferences':SCHEMES,'cases':[]}
SHOTS.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True); report['browserVersion']=b.version
 for width in WIDTHS:
  for scheme in SCHEMES:
   for route in ROUTES:
    ctx=b.new_context(viewport={'width':width,'height':900},color_scheme=scheme,reduced_motion='reduce'); page=ctx.new_page(); console=[]; errors=[]; failed=[]; responses=[]
    page.on('console',lambda m,a=console:a.append(m.text) if m.type=='error' else None); page.on('pageerror',lambda e,a=errors:a.append(str(e))); page.on('requestfailed',lambda q,a=failed:a.append({'url':q.url,'failure':q.failure})); page.on('response',lambda r,a=responses:a.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
    resp=page.goto(BASE+route,wait_until='networkidle'); page.keyboard.press('Tab'); focus=page.evaluate("() => {let e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,outlineStyle:s.outlineStyle,outlineWidth:s.outlineWidth,visible:e!==document.body&&(s.outlineStyle!=='none'||s.boxShadow!=='none')}}")
    audit=page.evaluate(JS); fav=page.locator('link[rel~="icon"]').first.get_attribute('href'); favresp=ctx.request.get(BASE+fav if fav.startswith('/') else fav)
    name=('home' if route=='/' else route.strip('/').replace('/','-'))+f'-{width}-{scheme}.png'; path=SHOTS/name; page.screenshot(path=str(path),full_page=True); digest=hashlib.sha256(path.read_bytes()).hexdigest()
    report['cases'].append({'route':route,'width':width,'osPreference':scheme,'status':resp.status if resp else None,'finalUrl':page.url,'consoleErrors':console,'pageErrors':errors,'failedRequests':failed,'failedResponses':responses,'favicon':{'url':fav,'status':favresp.status},'focus':focus,'screenshot':str(path),'screenshotSha256':digest,**audit}); ctx.close()
 b.close()
report['summary']={'caseCount':len(report['cases']),'failedCases':sum(bool(c['status']!=200 or c['consoleErrors'] or c['pageErrors'] or c['failedRequests'] or c['failedResponses'] or c['overflow'] or c['contrastFailures'] or c['favicon']['status']>=400 or not c['focus']['visible'] or not c['reducedMotion'] or c['theme'] not in (None,'light') or c['colorScheme']!='light') for c in report['cases']),'minimumContrast':min(x['ratio'] for c in report['cases'] for x in c['samples'])}
report['summary']['osPairScreenshotMismatches']=sum(report['cases'][i]['screenshotSha256']!=report['cases'][i+10]['screenshotSha256'] for i in range(0,100,20) for _ in [0])
(OUT/'browser-matrix.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['summary'],indent=2))
