(() => {
  'use strict';

  const originalRequestJson = window.requestJson;
  if (typeof originalRequestJson !== 'function') {
    console.error('Total RO Design feedback bridge could not find the host request helper.');
    return;
  }

  window.requestJson = async function twdsSuiteFeedbackRequest(url, options = {}, fallbackMessage = 'Request failed') {
    if (url !== '/api/feedback/report') {
      return originalRequestJson(url, options, fallbackMessage);
    }

    let legacy = {};
    try {
      legacy = JSON.parse(options.body || '{}') || {};
    } catch (_) {
      legacy = {};
    }
    const project = legacy.project && typeof legacy.project === 'object' ? legacy.project : {};
    const screenshots = Array.isArray(legacy.screenshots) ? legacy.screenshots : [];
    const context = String(legacy.context || 'calculation');
    const suitePayload = {
      application: 'ro',
      application_version: '0.2',
      category: /user feedback/i.test(context) ? 'general' : 'calculation',
      message: String(legacy.error || legacy.user_note || 'Total RO Design feedback'),
      project_id: String(project.visible_id || project.project_id || ''),
      project_revision: String(project.revision || project.project_revision || ''),
      workspace: String(legacy.active_mode || ''),
      diagnostic_context: {
        context,
        active_mode: legacy.active_mode || '',
        active_case: legacy.active_case ?? null,
        capture_error: legacy.capture_error || '',
        project,
      },
      screenshots,
    };

    const result = await originalRequestJson(
      '/api/suite/feedback/report',
      {...options, body: JSON.stringify(suitePayload)},
      fallbackMessage,
    );

    // Preserve the mature RO dialog contract while Suite Core remains the only
    // authoritative transport/storage workflow. "emailed" here is a legacy UI
    // success flag; Suite Core's returned message is the customer-facing truth.
    return {
      ...result,
      emailed: Boolean(result && result.ok),
      screenshots_saved: screenshots.length,
      capture_warning: legacy.capture_error || '',
    };
  };
})();
