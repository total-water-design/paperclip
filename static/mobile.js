/* Total Water Design Suite mobile bootstrap.
   No engineering calculations live here. This file only adapts presentation,
   connectivity feedback and install behavior around the hosted Suite. */
(function(){
  'use strict';

  const mqMobile = window.matchMedia('(max-width: 900px)');
  const standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  document.documentElement.classList.toggle('twds-standalone', standalone);

  function ensureNetworkBanner(){
    let banner = document.querySelector('.mobile-network-banner');
    if(!banner){
      banner = document.createElement('div');
      banner.className = 'mobile-network-banner';
      banner.setAttribute('role','status');
      banner.setAttribute('aria-live','polite');
      banner.textContent = 'Offline — engineering calculations require an internet connection.';
      document.body.appendChild(banner);
    }
    const update = () => document.body.classList.toggle('twds-offline', !navigator.onLine);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
  }

  function initRoNavigation(){
    const app = document.getElementById('calculatorApp');
    const sidebar = app && app.querySelector('.app-sidebar');
    if(!app || !sidebar) return;

    if(!sidebar.id) sidebar.id = 'twdsMobileSidebar';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'mobile-nav-toggle';
    toggle.setAttribute('aria-controls', sidebar.id);
    toggle.setAttribute('aria-expanded','false');
    toggle.setAttribute('aria-label','Open Total RO Design navigation');
    toggle.innerHTML = '<span class="mobile-nav-bars" aria-hidden="true"></span>';

    const backdrop = document.createElement('div');
    backdrop.className = 'mobile-nav-backdrop';
    backdrop.setAttribute('aria-hidden','true');

    document.body.appendChild(backdrop);
    document.body.appendChild(toggle);

    const setOpen = (open) => {
      document.body.classList.toggle('mobile-sidebar-open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? 'Close Total RO Design navigation' : 'Open Total RO Design navigation');
    };

    toggle.addEventListener('click', () => setOpen(!document.body.classList.contains('mobile-sidebar-open')));
    backdrop.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (event) => { if(event.key === 'Escape') setOpen(false); });
    sidebar.addEventListener('click', (event) => {
      if(mqMobile.matches && event.target.closest('button.tab, a')) setOpen(false);
    });

    const onViewportChange = (event) => { if(!event.matches) setOpen(false); };
    if(mqMobile.addEventListener) mqMobile.addEventListener('change', onViewportChange);
    else if(mqMobile.addListener) mqMobile.addListener(onViewportChange);
  }

  let deferredInstallPrompt = null;
  let installButton = null;

  function installHost(){
    return document.querySelector('.suite-public-header nav') ||
           document.querySelector('.suite-dashboard-header-actions') ||
           document.querySelector('#calculatorApp .topbar-actions');
  }

  function removeInstallButton(){
    if(installButton){ installButton.remove(); installButton = null; }
  }

  function exposeInstallButton(){
    if(standalone || installButton || !deferredInstallPrompt) return;
    const host = installHost();
    if(!host) return;
    installButton = document.createElement('button');
    installButton.type = 'button';
    installButton.className = 'mobile-install-button';
    installButton.textContent = 'Install app';
    installButton.addEventListener('click', async () => {
      if(!deferredInstallPrompt) return;
      deferredInstallPrompt.prompt();
      try { await deferredInstallPrompt.userChoice; } catch (_) {}
      deferredInstallPrompt = null;
      removeInstallButton();
    });
    host.appendChild(installButton);
  }

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    exposeInstallButton();
  });
  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    removeInstallButton();
  });

  function registerServiceWorker(){
    if(!('serviceWorker' in navigator) || !window.isSecureContext) return;
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/service-worker.js')
        .catch((error) => console.debug('TWDS static service worker not registered:', error));
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    ensureNetworkBanner();
    initRoNavigation();
    exposeInstallButton();
  });
  registerServiceWorker();
})();
