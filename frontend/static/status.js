(function () {
  const card = document.getElementById('status-card');
  const jobId = window.JOB_ID || (card && card.dataset.jobId);
  if (!jobId) {
    const m = document.getElementById('status-msg');
    if (m) m.textContent = 'Parâmetro "job" ausente.';
    return;
  }
  const bar = document.getElementById('status-bar');
  const msg = document.getElementById('status-msg');
  const readyBox = document.getElementById('status-ready');
  const errBox = document.getElementById('status-error');
  const errMsg = document.getElementById('status-error-msg');
  const countdownEl = document.getElementById('countdown');
  const link = document.getElementById('download-link');
  const filesEl = document.getElementById('status-files');

  const base = window.API_BASE || '';
  let expiresAt = null;
  link.href = base + '/files/' + jobId;

  function fmtTime(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }

  function setState(data) {
    bar.style.width = (data.progress || 0) + '%';
    msg.textContent = data.message || data.state || '';

    if (data.state === 'ready') {
      readyBox.hidden = false;
      errBox.hidden = true;
      expiresAt = Date.now() + ((data.expires_in != null ? data.expires_in : 600) * 1000);
      if (data.files && data.files.length > 1) {
        filesEl.textContent = `Arquivos (${data.files.length}) entregues em ZIP.`;
      } else {
        filesEl.textContent = '';
      }
      return true;
    }
    if (data.state === 'error') {
      readyBox.hidden = true;
      errBox.hidden = false;
      errMsg.textContent = data.error || 'Falha no download.';
      return true;
    }
    readyBox.hidden = true;
    errBox.hidden = true;
    return false;
  }

  const tick = setInterval(() => {
    if (!expiresAt) return;
    const left = Math.round((expiresAt - Date.now()) / 1000);
    if (left <= 0) {
      countdownEl.textContent = '00:00';
      msg.textContent = 'Arquivo expirado e removido do servidor.';
      link.removeAttribute('href');
      link.classList.add('disabled');
      clearInterval(tick);
      return;
    }
    countdownEl.textContent = fmtTime(left);
  }, 1000);

  async function poll() {
    const { ok, data } = await apiFetch(base + '/api/job/' + jobId);
    if (!ok) {
      msg.textContent = 'Download não encontrado ou já expirado.';
      return;
    }
    if (setState(data)) return;
    setTimeout(poll, window.STATUS_POLL_MS || 1500);
  }
  poll();
})();
