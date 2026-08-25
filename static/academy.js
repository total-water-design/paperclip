(() => {
  const moduleRoot = document.querySelector('[data-academy-module]');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const i18n = document.querySelector('#academy-i18n-data')?.dataset || {};

  function format(template, values = {}) {
    return String(template || '').replace(/\{(\w+)\}/g, (_, key) => values[key] ?? `{${key}}`);
  }

  async function postJSON(url, payload) {
    const headers = {'Content-Type': 'application/json'};
    if (csrf) headers['X-CSRFToken'] = csrf;
    const response = await fetch(url, {method: 'POST', headers, body: JSON.stringify(payload || {})});
    let data = {};
    try { data = await response.json(); } catch (_) { data = {error: i18n.unreadableResponse || 'The Academy service returned an unreadable response.'}; }
    if (!response.ok) throw new Error(data.error || i18n.saveFailed || 'The Academy could not save this activity.');
    return data;
  }

  function feedback(node, data) {
    if (!node) return;
    node.classList.remove('is-correct', 'is-review');
    node.classList.add('is-visible', data.correct ? 'is-correct' : 'is-review');
    const title = data.correct ? (i18n.goodReasoning || 'Good engineering reasoning') : (i18n.reviewReasoning || 'Review the reasoning');
    const hint = data.hint ? `<small><strong>${escapeHTML(i18n.hint || 'Hint')}</strong>${escapeHTML(data.hint)}</small>` : '';
    const scoreLabel = i18n.score || 'Score';
    node.innerHTML = `<strong>${escapeHTML(title)}</strong><span>${escapeHTML(data.feedback || data.error || '')}</span>${data.score !== undefined ? `<em>${escapeHTML(scoreLabel)}: ${Number(data.score).toFixed(1)}%</em>` : ''}${hint}`;
  }

  function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }

  function nextStep(section) {
    const next = section?.nextElementSibling;
    if (next?.matches?.('[data-academy-step]')) next.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  if (moduleRoot) {
    const moduleId = moduleRoot.dataset.academyModule;

    moduleRoot.querySelectorAll('[data-complete-concept]').forEach(button => {
      button.addEventListener('click', async () => {
        const section = button.closest('[data-academy-step]');
        const out = section.querySelector('[data-feedback]');
        button.disabled = true;
        try {
          await postJSON(`/academy/api/modules/${encodeURIComponent(moduleId)}/step`, {step_id: section.dataset.academyStep});
          feedback(out, {correct: true, feedback: i18n.conceptRecorded || 'Concept recorded. Carry this principle into the next decision.'});
          setTimeout(() => nextStep(section), 350);
        } catch (error) {
          feedback(out, {correct: false, error: error.message, feedback: error.message});
        } finally { button.disabled = false; }
      });
    });

    moduleRoot.querySelectorAll('[data-submit-quiz]').forEach(button => {
      button.addEventListener('click', async () => {
        const section = button.closest('[data-academy-step]');
        const selected = section.querySelector('input[type="radio"]:checked');
        const out = section.querySelector('[data-feedback]');
        if (!selected) return feedback(out, {correct: false, feedback: i18n.chooseAnswerFirst || 'Choose an answer first, then explain it to yourself before checking.'});
        button.disabled = true;
        try {
          const data = await postJSON(`/academy/api/modules/${encodeURIComponent(moduleId)}/assess`, {activity_id: section.dataset.academyStep, answer: Number(selected.value)});
          feedback(out, data);
          if (data.correct) setTimeout(() => nextStep(section), 700);
        } catch (error) { feedback(out, {correct: false, feedback: error.message}); }
        finally { button.disabled = false; }
      });
    });

    const practical = moduleRoot.querySelector('[data-step-kind="practical"]');
    if (practical) {
      const train = practical.querySelector('[data-academy-train]');
      const selected = [];
      const renderTrain = () => {
        train.innerHTML = '';
        selected.forEach((unit, index) => {
          const li = document.createElement('li');
          li.dataset.unitId = unit.id;
          const earlier = format(i18n.moveEarlier || 'Move {label} earlier', {label: unit.label});
          const later = format(i18n.moveLater || 'Move {label} later', {label: unit.label});
          const remove = format(i18n.removeUnit || 'Remove {label}', {label: unit.label});
          li.innerHTML = `<span><b>${escapeHTML(unit.label)}</b><span class="academy-train-controls"><button type="button" data-move="up" aria-label="${escapeHTML(earlier)}">↑</button><button type="button" data-move="down" aria-label="${escapeHTML(later)}">↓</button><button type="button" data-move="remove" aria-label="${escapeHTML(remove)}">×</button></span></span>`;
          li.querySelectorAll('[data-move]').forEach(control => control.addEventListener('click', () => {
            const action = control.dataset.move;
            if (action === 'remove') selected.splice(index, 1);
            if (action === 'up' && index > 0) [selected[index - 1], selected[index]] = [selected[index], selected[index - 1]];
            if (action === 'down' && index < selected.length - 1) [selected[index + 1], selected[index]] = [selected[index], selected[index + 1]];
            renderTrain();
          }));
          train.appendChild(li);
        });
        if (!selected.length) train.innerHTML = `<li><span><i>${escapeHTML(i18n.selectProcessBegin || 'Select a process from the toolbox to begin.')}</i></span></li>`;
      };
      renderTrain();
      practical.querySelectorAll('[data-unit-id]').forEach(button => button.addEventListener('click', () => {
        if (!selected.some(item => item.id === button.dataset.unitId)) selected.push({id: button.dataset.unitId, label: button.dataset.unitLabel});
        renderTrain();
      }));
      practical.querySelector('[data-clear-train]')?.addEventListener('click', () => { selected.splice(0); renderTrain(); });
      practical.querySelector('[data-submit-practical]')?.addEventListener('click', async event => {
        const button = event.currentTarget;
        const out = practical.querySelector('[data-feedback]');
        if (!selected.length) return feedback(out, {correct: false, feedback: i18n.buildTrainFirst || 'Build a treatment train before asking for a design review.'});
        button.disabled = true;
        try {
          const data = await postJSON(`/academy/api/modules/${encodeURIComponent(moduleId)}/assess`, {activity_id: practical.dataset.academyStep, answer: selected.map(item => item.id)});
          feedback(out, data);
          if (data.correct) setTimeout(() => nextStep(practical), 800);
        } catch (error) { feedback(out, {correct: false, feedback: error.message}); }
        finally { button.disabled = false; }
      });
    }

    moduleRoot.querySelectorAll('[data-submit-test]').forEach(button => {
      button.addEventListener('click', async () => {
        const section = button.closest('[data-academy-step]');
        const out = section.querySelector('[data-feedback]');
        const answer = {};
        section.querySelectorAll('[data-test-question]').forEach(fieldset => {
          const selected = fieldset.querySelector('input[type="radio"]:checked');
          if (selected) answer[fieldset.dataset.testQuestion] = Number(selected.value);
        });
        if (Object.keys(answer).length !== section.querySelectorAll('[data-test-question]').length) return feedback(out, {correct: false, feedback: i18n.answerAll || 'Answer every test question before submitting.'});
        button.disabled = true;
        try {
          const data = await postJSON(`/academy/api/modules/${encodeURIComponent(moduleId)}/assess`, {activity_id: section.dataset.academyStep, answer});
          feedback(out, data);
          if (data.module_state === 'completed') feedback(out, {...data, feedback: `${data.feedback} ${i18n.moduleComplete || 'Module complete — your progress has been recorded.'}`});
        } catch (error) { feedback(out, {correct: false, feedback: error.message}); }
        finally { button.disabled = false; }
      });
    });

    window.setInterval(async () => {
      if (document.visibilityState !== 'visible') return;
      try { await postJSON(`/academy/api/modules/${encodeURIComponent(moduleId)}/engagement`, {seconds: 60}); }
      catch (_) { /* Engagement credit must never interrupt learning. */ }
    }, 60000);
  }

  document.querySelector('[data-issue-diploma]')?.addEventListener('click', async event => {
    const button = event.currentTarget;
    const out = document.querySelector('[data-diploma-feedback]');
    button.disabled = true;
    try {
      const data = await postJSON('/academy/api/diploma/issue', {});
      const template = i18n.diplomaIssued || '{title} issued. Verification token: {token}';
      feedback(out, {correct: true, feedback: format(template, {title: data.title, token: data.verification_token})});
      button.hidden = true;
    } catch (error) { feedback(out, {correct: false, feedback: error.message}); }
    finally { button.disabled = false; }
  });
})();
