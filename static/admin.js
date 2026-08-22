(() => {
  'use strict';

  function closeDialog(dialog){
    if (!dialog) return;
    if (typeof dialog.close === 'function') dialog.close(); else dialog.removeAttribute('open');
  }
  function openDialog(id){
    const dialog=document.getElementById(id);
    if (!dialog) return;
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open','');
  }
  document.addEventListener('click', event => {
    const opener=event.target.closest('[data-open-dialog]');
    if (opener) { openDialog(opener.dataset.openDialog); return; }
    const closer=event.target.closest('[data-close-dialog]');
    if (closer) { closeDialog(closer.closest('dialog')); return; }
  });
  document.querySelectorAll('dialog').forEach(dialog => dialog.addEventListener('click', event => {
    if (event.target === dialog) closeDialog(dialog);
  }));

  function valueForCell(row,column,type){
    const cell=row.children[column];
    const raw=(cell?.dataset.sortValue ?? cell?.textContent ?? '').trim();
    if(type==='number') return Number(raw)||0;
    if(type==='date') { const n=Date.parse(raw); return Number.isFinite(n)?n:0; }
    return raw.toLowerCase();
  }
  function bindSorting(table){
    if(!table) return;
    table.querySelectorAll('.admin-sort').forEach(button => button.addEventListener('click', () => {
      const column=Number(button.dataset.column||0), type=button.dataset.type||'text';
      const current=button.dataset.direction==='asc'?'asc':'desc';
      const next=current==='asc'?'desc':'asc';
      table.querySelectorAll('.admin-sort').forEach(b=>{delete b.dataset.direction; b.classList.remove('sort-active');});
      button.dataset.direction=next; button.classList.add('sort-active');
      const tbody=table.tBodies[0]; if(!tbody) return;
      const rows=Array.from(tbody.querySelectorAll('tr')).filter(r=>r.matches('[data-user-row],[data-project-row]'));
      rows.sort((a,b)=>{
        const av=valueForCell(a,column,type), bv=valueForCell(b,column,type);
        const cmp=av<bv?-1:av>bv?1:0;
        return next==='asc'?cmp:-cmp;
      });
      rows.forEach(row=>tbody.appendChild(row));
    }));
  }

  const userTable=document.getElementById('userAdminTable');
  bindSorting(userTable);
  const userSearch=document.getElementById('userSearch');
  const statusFilter=document.getElementById('userStatusFilter');
  const roleFilter=document.getElementById('userRoleFilter');
  const tierFilter=document.getElementById('userTierFilter');
  function filterUsers(){
    if(!userTable) return;
    const q=(userSearch?.value||'').trim().toLowerCase();
    const status=statusFilter?.value||'', role=roleFilter?.value||'', tier=tierFilter?.value||'';
    let visible=0;
    userTable.querySelectorAll('[data-user-row]').forEach(row=>{
      const ok=(!q || (row.dataset.search||'').includes(q)) && (!status||row.dataset.status===status) && (!role||row.dataset.role===role) && (!tier||row.dataset.tier===tier);
      row.hidden=!ok; if(ok) visible++;
    });
    const count=document.getElementById('userVisibleCount'); if(count) count.textContent=String(visible);
  }
  [userSearch,statusFilter,roleFilter,tierFilter].forEach(el=>el?.addEventListener(el?.tagName==='INPUT'?'input':'change',filterUsers));

  const decisionDialog=document.getElementById('accountDecisionDialog');
  document.querySelectorAll('[data-account-decision]').forEach(button=>button.addEventListener('click',()=>{
    const action=button.dataset.accountDecision||'';
    const title={reject:'Reject account request',suspend:'Suspend account',cancel:'Cancel account'}[action]||'Account action';
    const form=document.getElementById('accountDecisionForm');
    if(form) form.action=button.dataset.actionUrl||'';
    const actionInput=document.getElementById('accountDecisionAction'); if(actionInput) actionInput.value=action;
    const heading=document.getElementById('accountDecisionTitle'); if(heading) heading.textContent=title;
    const user=document.getElementById('accountDecisionUser'); if(user) user.textContent=button.dataset.userName||'';
    const feedback=document.getElementById('accountDecisionFeedback'); if(feedback) { feedback.value=''; feedback.focus(); }
    const submit=document.getElementById('accountDecisionSubmit'); if(submit) submit.textContent=title;
    if(decisionDialog) openDialog(decisionDialog.id);
  }));

  const ipDialog=document.getElementById('ipHistoryDialog');
  document.querySelectorAll('[data-ip-url]').forEach(button=>button.addEventListener('click',async()=>{
    const title=document.getElementById('ipHistoryTitle'); if(title) title.textContent=`IP history · ${button.dataset.userLabel||'User'}`;
    const subtitle=document.getElementById('ipHistorySubtitle'); if(subtitle) subtitle.textContent='Successful login addresses only';
    const body=document.getElementById('ipHistoryBody'); if(body) body.innerHTML='<div class="admin-loading">Loading…</div>';
    if(ipDialog) openDialog(ipDialog.id);
    try{
      const response=await fetch(button.dataset.ipUrl,{credentials:'same-origin'});
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      const data=await response.json();
      if(!body) return;
      if(!data.addresses?.length){body.innerHTML='<div class="admin-loading">No successful login IP addresses recorded yet.</div>';return;}
      const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      body.innerHTML=`<table class="admin-ip-table"><thead><tr><th>IP address</th><th>Logins</th><th>First seen</th><th>Last seen</th><th>Last browser / device</th></tr></thead><tbody>${data.addresses.map(row=>`<tr><td><strong>${esc(row.ip_address)}</strong></td><td>${Number(row.login_count||0)}</td><td>${esc(row.first_seen_at||'—')}</td><td>${esc(row.last_seen_at||'—')}</td><td>${esc(row.last_user_agent||'—')}</td></tr>`).join('')}</tbody></table>`;
    }catch(error){if(body) body.innerHTML='<div class="auth-flash auth-flash-error">Could not load IP history.</div>';}
  }));

  const projectTable=document.getElementById('projectAdminTable');
  bindSorting(projectTable);
  const projectSearch=document.getElementById('projectSearch');
  const productFilter=document.getElementById('projectProductFilter');
  const revisionFilter=document.getElementById('projectRevisionFilter');
  function filterProjects(){
    if(!projectTable) return;
    const q=(projectSearch?.value||'').trim().toLowerCase(), product=productFilter?.value||'', rev=revisionFilter?.value||'';
    let visible=0;
    projectTable.querySelectorAll('[data-project-row]').forEach(row=>{
      const revision=Number(row.dataset.revision||0);
      const revOk=!rev || (rev==='0'&&revision===0) || (rev==='gt0'&&revision>0);
      const ok=(!q||(row.dataset.search||'').includes(q)) && (!product||row.dataset.product===product) && revOk;
      row.hidden=!ok; if(ok) visible++;
    });
    const count=document.getElementById('projectVisibleCount'); if(count) count.textContent=String(visible);
  }
  [projectSearch,productFilter,revisionFilter].forEach(el=>el?.addEventListener(el?.tagName==='INPUT'?'input':'change',filterProjects));

  const projectDialog=document.getElementById('projectJsonDialog');
  document.querySelectorAll('[data-project-json-url]').forEach(button=>button.addEventListener('click',async()=>{
    const title=document.getElementById('projectJsonTitle'); if(title) title.textContent=`Saved project · ${button.dataset.projectLabel||''}`;
    const subtitle=document.getElementById('projectJsonSubtitle'); if(subtitle) subtitle.textContent='Read-only database snapshot';
    const body=document.getElementById('projectJsonBody'); if(body) body.textContent='Loading…';
    if(projectDialog) openDialog(projectDialog.id);
    try{
      const response=await fetch(button.dataset.projectJsonUrl,{credentials:'same-origin'});
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      const data=await response.json();
      if(body) body.textContent=JSON.stringify(data,null,2);
    }catch(error){if(body) body.textContent=`Could not load saved project snapshot: ${error.message||error}`;}
  }));
})();
