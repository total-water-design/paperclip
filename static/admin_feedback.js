(() => {
  "use strict";
  function csrf(){return document.querySelector('meta[name="csrf-token"]')?.content||''}
  function applyDateFilter(){
    const params=new URLSearchParams(window.location.search);
    const from=params.get('date_from')||'';
    const to=params.get('date_to')||'';
    let visible=0;
    document.querySelectorAll('[data-feedback-row]').forEach(row=>{
      const created=row.dataset.createdDate||'';
      const show=(!from||!created||created>=from)&&(!to||!created||created<=to);
      row.hidden=!show;if(show)visible+=1;
    });
    const count=document.getElementById('feedbackVisibleCount');if(count)count.textContent=String(visible);
  }
  document.addEventListener('click',async(event)=>{
    const button=event.target.closest('[data-feedback-retry]');
    if(!button)return;
    button.disabled=true;
    try{
      const response=await fetch(`/api/suite/admin/feedback/${button.dataset.feedbackRetry}/retry`,{
        method:'POST',credentials:'same-origin',headers:{'X-CSRFToken':csrf()}
      });
      const result=await response.json().catch(()=>({}));
      if(!response.ok||!result.ok)throw new Error(result.error||result.detail||'Retry failed');
      window.location.reload();
    }catch(error){
      window.alert(error.message||String(error));
      button.disabled=false;
    }
  });
  document.addEventListener('DOMContentLoaded',applyDateFilter);
})();
