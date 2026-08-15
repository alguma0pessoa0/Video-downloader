window.QUALITY_LABELS = {
  video: {
    best: 'Melhor qualidade',
    '2160': '2160p (4K)',
    '1440': '1440p (2K)',
    '1080': '1080p',
    '720': '720p',
    '480': '480p',
    '360': '360p',
    '240': '240p',
    '144': '144p',
  },
  audio: {
    best: 'Melhor (formato original)',
    '320': 'MP3 320 kbps',
    '192': 'MP3 192 kbps',
    '128': 'MP3 128 kbps',
  },
};

async function apiFetch(url, options) {
  const res = await fetch(url, options);
  let data = {};
  try {
    data = await res.json();
  } catch (_) {
    /* resposta não-JSON */
  }
  return { ok: res.ok, status: res.status, data };
}

function fmtBytes(n) {
  if (n == null || isNaN(n)) return '';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = n;
  let i = 0;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i += 1;
  }
  return size.toFixed(1) + ' ' + units[i];
}
