(() => {
  "use strict";
  const STORAGE_KEY="twds-theme";
  const VALID_THEMES=new Set(["system","light","dark"]);
  const CALC_STATES=Object.freeze({idle:"Calculate",validating:"Validating…",calculating:"Calculating…",converging:"Converging…",converged:"Converged",attention:"Needs attention",failed:"Calculation failed",stale:"Recalculate"});
  let dirty=false;

  function resolvedTheme(value){if(value==="light"||value==="dark")return value;return window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}
  function applyTheme(value){const requested=VALID_THEMES.has(value)?value:"system";document.documentElement.dataset.theme=resolvedTheme(requested);document.documentElement.dataset.themePreference=requested;document.querySelectorAll("[data-twds-theme-select]").forEach(s=>s.value=requested);return requested}
  function setTheme(value){const requested=VALID_THEMES.has(value)?value:"system";try{localStorage.setItem(STORAGE_KEY,requested)}catch(_){ }return applyTheme(requested)}
  function loadTheme(){let saved="system";try{saved=localStorage.getItem(STORAGE_KEY)||"system"}catch(_){ }return applyTheme(saved)}

  function setCalculationState(target,state,detail=""){
    const el=typeof target==="string"?document.querySelector(target):target;if(!el||!CALC_STATES[state])return false;
    el.dataset.twdsCalculateState=state;el.setAttribute("aria-busy",["validating","calculating","converging"].includes(state)?"true":"false");
    const label=el.querySelector("[data-twds-calculate-label]");if(label)label.textContent=CALC_STATES[state];
    const live=document.querySelector("[data-twds-calculation-live]");if(live)live.textContent=detail||CALC_STATES[state];return true;
  }

  function markDirty(value=true){dirty=Boolean(value);document.querySelectorAll("[data-twds-unsaved]").forEach(el=>el.hidden=!dirty);document.querySelectorAll("[data-twds-project-bar]").forEach(el=>el.dataset.twdsDirty=dirty?"true":"false")}

  function initTheme(){loadTheme();document.querySelectorAll("[data-twds-theme-select]").forEach(s=>s.addEventListener("change",()=>setTheme(s.value)));if(window.matchMedia){const mq=window.matchMedia("(prefers-color-scheme: dark)");if(mq.addEventListener)mq.addEventListener("change",()=>{if(document.documentElement.dataset.themePreference==="system")applyTheme("system")})}}
  function initDirty(){document.querySelectorAll("[data-twds-dirty-watch]").forEach(root=>{root.addEventListener("input",e=>{if(e.target.matches("input,select,textarea"))markDirty(true)});root.addEventListener("change",e=>{if(e.target.matches("input,select,textarea"))markDirty(true)})});window.addEventListener("beforeunload",e=>{if(!dirty)return;e.preventDefault();e.returnValue=""})}
  function initProjectActions(){document.addEventListener("click",e=>{const b=e.target.closest("[data-twds-project-action]");if(!b)return;document.dispatchEvent(new CustomEvent("twds:project-action",{bubbles:true,detail:{action:b.dataset.twdsProjectAction,source:b}}))})}
  function initCalcForms(){document.querySelectorAll("[data-twds-calc-form]").forEach(form=>form.addEventListener("submit",()=>{const b=form.querySelector("[data-twds-calculate-state]");if(b&&b.dataset.twdsCalculateState!=="calculating")setCalculationState(b,"validating")}))}

  window.TWDSAppUI=Object.freeze({calculationStates:CALC_STATES,setCalculationState,markDirty,setTheme,get dirty(){return dirty}});
  document.addEventListener("DOMContentLoaded",()=>{initTheme();initDirty();initProjectActions();initCalcForms()});
})();
