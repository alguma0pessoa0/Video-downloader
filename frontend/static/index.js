(function () {
  const form = document.getElementById('inspect-form');
  if (!form) return;

  const urlInput = document.getElementById('url');
  const mediaSelect = document.getElementById('media_type');
  const qualitySelect = document.getElementById('quality');
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnDownload = document.getElementById('btn-download');
  const msg = document.getElementById('form-msg');
  const result = document.getElementById('result');
  const resultTitle = document.getElementById('result-title');
  const resultThumb = document.getElementById('result-thumb');
  const resultType = document.getElementById('result-type');
  const resultPlaylist = document.getElementById('result-playlist');
  const resultSize = document.getElementById('result-size');
  const resultError = document.getElementById('result-error');

  let current = null;

  function showMsg(text, isError) {
    msg.textContent = text;
    msg.hidden = !text;
    msg.className = 'msg' + (isError ? ' error' : '');
  }

  function reset() {
    btnDownload.disabled = true;
    qualitySelect.disabled = true;
    qualitySelect.innerHTML = '<option value="">Analise o link primeiro</option>';
    result.hidden = true;
    resultError.hidden = true;
    current = null;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;
    btnAnalyze.disabled = true;
    reset();
    showMsg('Analisando link...', false);

    const { ok, data } = await apiFetch((window.API_BASE || '') + '/inspect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, media_type: mediaSelect.value }),
    });

    btnAnalyze.disabled = false;
    if (!ok) {
      showMsg(data.error || 'Erro ao analisar o link.', true);
      return;
    }
    showMsg('', false);
    renderResult(data, url);
  });

  function renderResult(data, url) {
    result.hidden = false;
    resultTitle.textContent = data.title || 'Conteúdo';
    resultType.textContent = mediaSelect.value === 'video' ? 'Vídeo' : 'Áudio';

    resultPlaylist.hidden = !data.is_playlist;
    if (data.is_playlist) {
      let t = 'Playlist';
      if (data.playlist_count) t += ` com ${data.playlist_count} item(ns)`;
      if (data.playlist_truncated) t += ` — apenas os primeiros ${window.MAX_PLAYLIST_ITEMS} serão baixados`;
      resultPlaylist.textContent = t + '.';
    }

    resultSize.hidden = !data.size_est;
    if (data.size_est) resultSize.textContent = 'Tamanho estimado: ' + fmtBytes(data.size_est);

    if (data.thumbnail) {
      resultThumb.src = data.thumbnail;
      resultThumb.hidden = false;
    } else {
      resultThumb.hidden = true;
    }

    qualitySelect.innerHTML = '';
    const labels = window.QUALITY_LABELS[mediaSelect.value] || {};
    for (const q of data.qualities || []) {
      const opt = document.createElement('option');
      opt.value = q;
      opt.textContent = labels[q] || q;
      qualitySelect.appendChild(opt);
    }
    qualitySelect.disabled = false;
    btnDownload.disabled = false;
    current = { url, media_type: mediaSelect.value, title: data.title || '' };
  }

  btnDownload.addEventListener('click', async () => {
    if (!current) return;
    btnDownload.disabled = true;
    showMsg('Iniciando download...', false);
    const { ok, data } = await apiFetch((window.API_BASE || '') + '/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...current, quality: qualitySelect.value }),
    });
    if (!ok) {
      btnDownload.disabled = false;
      showMsg(data.error || 'Erro ao iniciar o download.', true);
      return;
    }
    location.href = (window.STATUS_PATH || '/status/') + data.job_id;
  });

  mediaSelect.addEventListener('change', reset);
})();
