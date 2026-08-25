(() => {
  'use strict';

  const locale = document.documentElement.dataset.academyLocale || 'en';
  if (locale === 'en') return;

  const COPY = {
    'es-419': {
      endorsement: 'Parte de Total Water Design Suite',
      feedback: 'Comentarios', appearance: 'Apariencia', system: 'Sistema', light: 'Claro', dark: 'Oscuro',
      suiteReturn: '← Suite', application: 'APLICACIÓN', myAccount: 'Mi cuenta', manageUsers: 'Administrar usuarios',
      projectDatabase: 'Base de datos de proyectos', signOut: 'Cerrar sesión',
      feedbackEyebrow: 'COMENTARIOS DE LA SUITE', feedbackTitle: 'Cuéntanos qué encontraste',
      feedbackCopy: 'La aplicación, el proyecto y el espacio de trabajo actual se adjuntan automáticamente. La captura de pantalla es opcional.',
      closeFeedback: 'Cerrar comentarios', feedbackType: 'Tipo de comentario', description: 'Descripción',
      placeholder: 'Describe qué ocurrió, qué esperabas o qué podría mejorarse.',
      includeScreenshot: 'Incluir una captura de pantalla de la pestaña actual cuando el navegador lo permita',
      cancel: 'Cancelar', submit: 'Enviar comentarios',
      categories: {
        calculation: 'Cálculo / inquietud sobre resultados', usability: 'Usabilidad / flujo de trabajo',
        data: 'Base de datos / datos de producto', report: 'Informe', bug: 'Problema de la aplicación',
        suggestion: 'Sugerencia', general: 'Comentario general'
      },
      describeFirst: 'Describe el comentario antes de enviarlo.', preparing: 'Preparando comentarios…',
      submitting: 'Enviando comentarios…', failed: 'No se pudieron enviar los comentarios.',
      received: (ticket) => `Gracias. Tus comentarios se recibieron correctamente. Referencia: ${ticket}.`
    },
    ar: {
      endorsement: 'جزء من Total Water Design Suite',
      feedback: 'الملاحظات', appearance: 'المظهر', system: 'النظام', light: 'فاتح', dark: 'داكن',
      suiteReturn: 'العودة إلى المنظومة →', application: 'التطبيق', myAccount: 'حسابي', manageUsers: 'إدارة المستخدمين',
      projectDatabase: 'قاعدة بيانات المشاريع', signOut: 'تسجيل الخروج',
      feedbackEyebrow: 'ملاحظات المنظومة', feedbackTitle: 'أخبرنا بما وجدته',
      feedbackCopy: 'يتم إرفاق التطبيق والمشروع ومساحة العمل الحالية تلقائياً. لقطة الشاشة اختيارية.',
      closeFeedback: 'إغلاق نافذة الملاحظات', feedbackType: 'نوع الملاحظة', description: 'الوصف',
      placeholder: 'صف ما حدث وما كنت تتوقعه أو ما الذي يمكن تحسينه.',
      includeScreenshot: 'إرفاق لقطة شاشة للتبويب الحالي عندما يسمح المتصفح بذلك',
      cancel: 'إلغاء', submit: 'إرسال الملاحظات',
      categories: {
        calculation: 'ملاحظة على الحساب / النتيجة', usability: 'سهولة الاستخدام / سير العمل',
        data: 'قاعدة البيانات / بيانات المنتج', report: 'التقرير', bug: 'مشكلة في التطبيق',
        suggestion: 'اقتراح', general: 'ملاحظة عامة'
      },
      describeFirst: 'يرجى وصف الملاحظة قبل الإرسال.', preparing: 'جارٍ تجهيز الملاحظات…',
      submitting: 'جارٍ إرسال الملاحظات…', failed: 'تعذر إرسال الملاحظات.',
      received: (ticket) => `شكراً لك. تم استلام ملاحظاتك بنجاح. المرجع: ${ticket}.`
    }
  };

  const copy = COPY[locale];
  if (!copy) return;
  const qs = (selector, root = document) => root.querySelector(selector);

  function setText(selector, value, root = document) {
    const node = qs(selector, root);
    if (node && value) node.textContent = value;
  }

  function localizeShell() {
    setText('.twds-app-identity__copy span', copy.endorsement);
    setText('[data-twds-feedback-open]', copy.feedback);
    setText('.twds-theme-control > span', copy.appearance);
    const theme = qs('[data-twds-theme-select]');
    if (theme) {
      theme.setAttribute('aria-label', copy.appearance);
      [['system', copy.system], ['light', copy.light], ['dark', copy.dark]].forEach(([value, label]) => {
        const option = theme.querySelector(`option[value="${value}"]`);
        if (option) option.textContent = label;
      });
    }
    setText('.twds-suite-return', copy.suiteReturn);
    setText('.twds-app-nav__heading > span', copy.application);

    document.querySelectorAll('.twds-account-menu__panel a').forEach(link => {
      const original = link.textContent.trim();
      if (original === 'My account') link.textContent = copy.myAccount;
      if (original === 'Manage users') link.textContent = copy.manageUsers;
      if (original === 'Project database') link.textContent = copy.projectDatabase;
    });
    document.querySelectorAll('.twds-account-menu__panel button').forEach(button => {
      if (button.textContent.trim() === 'Sign out') button.textContent = copy.signOut;
    });

    const dialog = qs('[data-twds-feedback-dialog]');
    if (!dialog) return;
    setText('header > div > span', copy.feedbackEyebrow, dialog);
    setText('#twdsFeedbackTitle', copy.feedbackTitle, dialog);
    setText('header > div > p', copy.feedbackCopy, dialog);
    const close = qs('[data-twds-feedback-close]', dialog);
    if (close) close.setAttribute('aria-label', copy.closeFeedback);
    setText('label:has(select[name="category"]) > span', copy.feedbackType, dialog);
    setText('label:has(textarea[name="message"]) > span', copy.description, dialog);
    const textarea = qs('textarea[name="message"]', dialog);
    if (textarea) textarea.placeholder = copy.placeholder;
    setText('.twds-feedback-check > span', copy.includeScreenshot, dialog);
    const cancel = dialog.querySelector('footer [data-twds-feedback-close]');
    if (cancel) cancel.textContent = copy.cancel;
    const submit = qs('[data-twds-feedback-submit]', dialog);
    if (submit) submit.textContent = copy.submit;
    const category = qs('select[name="category"]', dialog);
    if (category) Object.entries(copy.categories).forEach(([value, label]) => {
      const option = category.querySelector(`option[value="${value}"]`);
      if (option) option.textContent = label;
    });

    const status = qs('[data-twds-feedback-status]', dialog);
    if (status && !status.dataset.academyI18nObserver) {
      status.dataset.academyI18nObserver = '1';
      const translateStatus = () => {
        const text = status.textContent.trim();
        if (text === 'Please describe the feedback before submitting.') status.textContent = copy.describeFirst;
        else if (text === 'Preparing feedback…') status.textContent = copy.preparing;
        else if (text === 'Submitting feedback…') status.textContent = copy.submitting;
        else if (text === 'Feedback could not be submitted.') status.textContent = copy.failed;
        else {
          const received = text.match(/^Thank you\. Your feedback was received successfully\. Reference: (TWDS-[A-Z0-9-]+)\.$/);
          if (received) status.textContent = copy.received(received[1]);
          const fallback = text.match(/^Feedback (TWDS-[A-Z0-9-]+) was received\.$/);
          if (fallback) status.textContent = copy.received(fallback[1]);
        }
      };
      new MutationObserver(translateStatus).observe(status, {childList: true, subtree: true, characterData: true});
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', localizeShell, {once: true});
  else localizeShell();
})();
