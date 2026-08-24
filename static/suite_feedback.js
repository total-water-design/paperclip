(() => {
  "use strict";

  const qs=(s,r=document)=>r.querySelector(s);
  const csrf=()=>qs('meta[name="csrf-token"]')?.content||"";

  function shell(){return qs('[data-twds-app-shell]')}
  function projectContext(){
    return {
      project_id:qs('[data-twds-project-id]')?.textContent?.trim()||"",
      project_revision:qs('[data-twds-project-revision]')?.textContent?.trim()||"",
      project_name:qs('[data-twds-project-name]')?.textContent?.trim()||"",
      workspace:qs('.twds-workspace-heading h1')?.textContent?.trim()||document.title,
    };
  }

  async function captureCurrentTab(){
    if(!navigator.mediaDevices?.getDisplayMedia)return null;
    let stream=null;
    try{
      stream=await navigator.mediaDevices.getDisplayMedia({video:{displaySurface:'browser'},audio:false,preferCurrentTab:true,selfBrowserSurface:'include'});
      const video=document.createElement('video');
      video.srcObject=stream;video.muted=true;
      await video.play();
      if(video.readyState<2)await new Promise(resolve=>video.addEventListener('loadeddata',resolve,{once:true}));
      const canvas=document.createElement('canvas');
      canvas.width=Math.min(video.videoWidth||window.innerWidth,2400);
      canvas.height=Math.round(canvas.width*((video.videoHeight||window.innerHeight)/(video.videoWidth||window.innerWidth)));
      canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
      return {label:'current_workspace',data_url:canvas.toDataURL('image/png',0.88)};
    }catch(_){return null}
    finally{stream?.getTracks()?.forEach(track=>track.stop())}
  }

  async function diagnosticContext(){
    try{
      if(typeof window.TWDSFeedbackContextProvider==='function'){
        const value=await window.TWDSFeedbackContextProvider();
        if(value&&typeof value==='object')return value;
      }
    }catch(_){ }
    return {};
  }

  function openDialog(){
    const d=qs('[data-twds-feedback-dialog]');if(!d)return;
    const status=qs('[data-twds-feedback-status]',d);if(status)status.textContent='';
    if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');
    setTimeout(()=>qs('textarea[name="message"]',d)?.focus(),0);
  }
  function closeDialog(){const d=qs('[data-twds-feedback-dialog]');if(!d)return;if(typeof d.close==='function')d.close();else d.removeAttribute('open')}

  async function submitFeedback(form){
    const d=qs('[data-twds-feedback-dialog]');
    const status=qs('[data-twds-feedback-status]',d);const submit=qs('[data-twds-feedback-submit]',d);
    const message=String(new FormData(form).get('message')||'').trim();
    if(message.length<3){if(status)status.textContent='Please describe the feedback before submitting.';return}
    submit.disabled=true;if(status)status.textContent='Preparing feedback…';
    try{
      const include=qs('input[name="include_screenshot"]',form)?.checked;
      const screenshot=include?await captureCurrentTab():null;
      if(status)status.textContent='Submitting feedback…';
      const root=shell();const context=projectContext();
      const payload={
        application:root?.dataset.appName||root?.dataset.appId||'suite',
        application_id:root?.dataset.appId||'unknown',
        application_version:root?.dataset.appVersion||'',
        category:String(new FormData(form).get('category')||'general'),
        message,
        ...context,
        page:window.location.pathname,
        screenshots:screenshot?[screenshot]:[],
        diagnostic_context:await diagnosticContext(),
      };
      const headers={'Content-Type':'application/json'};const token=csrf();if(token)headers['X-CSRFToken']=token;
      const response=await fetch('/api/suite/feedback/report',{method:'POST',credentials:'same-origin',headers,body:JSON.stringify(payload)});
      const result=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(result.error||'Feedback could not be submitted.');
      form.reset();
      if(status){status.className='twds-feedback-status '+(result.emailed?'success':'warning');status.textContent=result.message||`Feedback ${result.ticket} was received.`}
      if(result.emailed)setTimeout(closeDialog,1800);
    }catch(error){if(status){status.className='twds-feedback-status error';status.textContent=error.message||String(error)}}
    finally{submit.disabled=false}
  }

  document.addEventListener('DOMContentLoaded',()=>{
    document.addEventListener('click',event=>{if(event.target.closest('[data-twds-feedback-open]'))openDialog();if(event.target.closest('[data-twds-feedback-close]'))closeDialog()});
    qs('[data-twds-feedback-form]')?.addEventListener('submit',event=>{event.preventDefault();submitFeedback(event.currentTarget)});
    const d=qs('[data-twds-feedback-dialog]');d?.addEventListener('click',event=>{if(event.target===d)closeDialog()});
  });

  window.TWDSFeedback=Object.freeze({open:openDialog,close:closeDialog});
})();
