import json
import os
import re
import time
import urllib.request

import yt_dlp

import config

_MD_ENTRY = re.compile(r'^ - \*\*(.+?)\*\*: ?(.*)$')


def _maybe_unescape(s):
    if '\\u' in s:
        try:
            return s.encode('utf-8').decode('unicode_escape')
        except Exception:
            pass
    return s


def _clean_desc(text):
    text = re.sub(r'\[\*.*?\*\]\(## "netrc machine"\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = text.replace('**Currently broken**', '').replace('`', '')
    return re.sub(r'\s+', ' ', text).strip()


def _fetch_markdown_descs():
    cache_path = os.path.join(config.BASE_DIR, 'sites_desc.json')
    now = time.time()
    try:
        if os.path.exists(cache_path) and now - os.path.getmtime(cache_path) < config.SITES_DESC_CACHE_TTL:
            with open(cache_path, encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass

    data = {}
    try:
        with urllib.request.urlopen(config.SITES_FETCH_URL, timeout=10) as resp:
            text = resp.read().decode('utf-8', 'ignore')
        for line in text.splitlines():
            m = _MD_ENTRY.match(line)
            if m:
                name = _maybe_unescape(m.group(1).strip())
                desc = _clean_desc(m.group(2))
                if name:
                    data[name] = desc
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass
    except Exception:
        if os.path.exists(cache_path):
            try:
                with open(cache_path, encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
    return data


def _extractor_list():
    out = []
    try:
        for ie in yt_dlp.list_extractors():
            try:
                working = bool(ie.working())
            except Exception:
                working = True
            out.append({
                'name': ie.IE_NAME,
                'desc': getattr(ie, 'IE_DESC', None) or '',
                'working': working,
            })
    except Exception:
        pass
    return out


def get_site_list():
    local = _extractor_list()
    local_names = {e['name'] for e in local}
    md = _fetch_markdown_descs()

    merged = []
    for e in local:
        merged.append({**e, 'desc': md.get(e['name'], e['desc'])})
    for name, desc in md.items():
        if name not in local_names:
            merged.append({'name': name, 'desc': desc, 'working': None, 'extra': True})

    merged.sort(key=lambda x: x['name'].lower())
    return merged
