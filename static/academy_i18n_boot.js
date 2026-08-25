(() => {
  const script = document.currentScript;
  const locale = script?.dataset.academyLocale || 'en';
  const direction = script?.dataset.academyDir === 'rtl' ? 'rtl' : 'ltr';
  document.documentElement.lang = locale;
  document.documentElement.dir = direction;
  document.documentElement.dataset.academyLocale = locale;
  document.documentElement.dataset.academyDirection = direction;
})();
