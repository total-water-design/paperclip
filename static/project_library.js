(() => {
  "use strict";
  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||'';
  const status=document.getElementById('projectReportStatus');
  function show(message,isError=false){if(!status)return;status.hidden=false;status.innerHTML=`<strong>${isError?'Report could not be generated':'Report ready'}</strong><p>${String(message||'')}</p>`;}
  document.addEventListener('click',async(e)=>{
    const button=e.target.closest('[data-full-report]');if(!button)return;
    button.disabled=true;button.textContent='Generating…';
    try{
      const response=await fetch(`/api/suite/projects/${button.dataset.fullReport}/full-report`,{method:'POST',headers:{'X-CSRFToken':csrf},credentials:'same-origin'});
      const data=await response.json();if(!response.ok)throw new Error(data.error||'Report generation failed.');
      const report=data.report||{};
      if(report.url){show('The report was generated from the saved project revision. Opening it now.');window.open(report.url,'_blank','noopener');}
      else if(report.filename){show(`The report was generated as ${report.filename}.`);}
      else{show('The report provider completed successfully.');}
    }catch(error){show(error.message||String(error),true);}
    finally{button.disabled=false;button.textContent='Generate Full Report';}
  });
})();
