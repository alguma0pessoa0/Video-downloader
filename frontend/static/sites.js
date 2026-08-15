(function () {
  const list = document.getElementById('site-list');
  if (!list) return;

  const filter = document.getElementById('site-filter');
  const countEl = document.getElementById('site-count');
  const sites = window.SITES || [];

  const BADGES = {
    ok: { text: 'funciona', cls: 'badge-ok' },
    broken: { text: 'quebrado', cls: 'badge-broken' },
    extra: { text: 'precisa de atualização', cls: 'badge-extra' },
  };

  function render(q) {
    const needle = q.trim().toLowerCase();
    const items = needle
      ? sites.filter(
          (s) =>
            s.name.toLowerCase().includes(needle) ||
            ((s.desc || '').toLowerCase().includes(needle))
        )
      : sites;

    countEl.textContent = `Mostrando ${items.length} de ${sites.length} extractors`;
    list.innerHTML = '';

    for (const s of items) {
      const li = document.createElement('li');

      const name = document.createElement('span');
      name.className = 'site-name';
      name.textContent = s.name;
      li.appendChild(name);

      if (s.desc) {
        const d = document.createElement('span');
        d.className = 'site-desc';
        d.textContent = s.desc;
        li.appendChild(d);
      }

      let badge = BADGES.ok;
      if (s.working === false) badge = BADGES.broken;
      else if (s.extra) badge = BADGES.extra;

      const b = document.createElement('span');
      b.className = 'badge ' + badge.cls;
      b.textContent = badge.text;
      li.appendChild(b);

      list.appendChild(li);
    }
  }

  filter.addEventListener('input', () => render(filter.value));
  render('');
})();
