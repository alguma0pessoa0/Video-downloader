import os
import threading
import time
from collections import OrderedDict

import yt_dlp
from yt_dlp.utils import DownloadError

import config

VIDEO_QUALITIES = ['best', '2160', '1440', '1080', '720', '480', '360', '240', '144']
AUDIO_QUALITIES = ['best', '320', '192', '128']

AUDIO_QUALITY_MAP = {'320': 0, '192': 5, '128': 9}


class _Logger:
    def __init__(self, cb):
        self._cb = cb

    def debug(self, msg):
        pass

    def warning(self, msg):
        self._cb(str(msg))

    def error(self, msg):
        self._cb(str(msg))


class InspectCache:
    def __init__(self, ttl=300, maxsize=64):
        self._cache = OrderedDict()
        self._ttl = ttl
        self._max = maxsize
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            val = self._cache.get(key)
            if val and time.time() - val[0] < self._ttl:
                return val[1]
            if val:
                del self._cache[key]
        return None

    def put(self, key, value):
        with self._lock:
            self._cache[key] = (time.time(), value)
            self._cache.move_to_end(key)
            while len(self._cache) > self._max:
                self._cache.popitem(last=False)


inspect_cache = InspectCache()


def _flat_options():
    return {
        'skip_download': True,
        'extract_flat': True,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'retries': 2,
    }


def _full_options():
    return {
        'skip_download': True,
        'extract_flat': False,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'retries': 2,
    }


def _generic_qualities(media_type):
    return VIDEO_QUALITIES if media_type == 'video' else AUDIO_QUALITIES


def _estimate_size(info):
    fmts = info.get('formats') or []
    videos = [
        f for f in fmts
        if f.get('height') and (f.get('vcodec') or '').lower() != 'none'
    ]
    audios = [
        f for f in fmts
        if (f.get('acodec') or '').lower() not in ('none', '')
    ]

    def size_of(f):
        return f.get('filesize') or f.get('filesize_approx') or 0

    vsize = max((size_of(f) for f in videos), default=0)
    asize = max((size_of(f) for f in audios), default=0)
    total = vsize + asize
    return int(total) if total else None


def _inspect(url, media_type):
    try:
        with yt_dlp.YoutubeDL(_flat_options()) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        return {'error': f'Não foi possível analisar o URL: {exc}'}

    if info is None:
        return {'error': 'Nenhuma informação encontrada para este URL.'}
    if isinstance(info, list):
        info = {
            '_type': 'playlist',
            'title': 'Lista de vídeos',
            'entries': list(info),
        }
    if not isinstance(info, dict):
        return {'error': 'Resposta inesperada do site.'}

    itype = info.get('_type')
    if itype in ('playlist', 'multi_video'):
        entries = info.get('entries') or []
        total = info.get('playlist_count') or len(entries) or None
        return {
            'is_playlist': True,
            'title': info.get('title') or 'Playlist',
            'playlist_count': total,
            'playlist_truncated': bool(total and total > config.MAX_PLAYLIST_ITEMS),
            'media_type': media_type,
            'qualities': _generic_qualities(media_type),
            'thumbnail': None,
            'duration': None,
            'size_est': None,
        }

    full = info
    try:
        with yt_dlp.YoutubeDL(_full_options()) as ydl:
            full = ydl.extract_info(url, download=False)
    except Exception:
        full = info

    if not isinstance(full, dict):
        full = info

    heights = sorted(
        {
            int(f.get('height'))
            for f in (full.get('formats') or [])
            if f.get('height') and int(f.get('height')) >= 144
        }
    )

    if media_type == 'video':
        qualities = ['best'] + [str(h) for h in reversed(heights)]
    else:
        qualities = list(AUDIO_QUALITIES)

    size_est = _estimate_size(full)

    return {
        'is_playlist': False,
        'title': full.get('title') or info.get('title') or 'Vídeo',
        'duration': full.get('duration'),
        'thumbnail': full.get('thumbnail'),
        'media_type': media_type,
        'qualities': qualities,
        'size_est': size_est,
        'oversized': bool(size_est and size_est > config.MAX_FILE_SIZE),
        'size_limit': config.MAX_FILE_SIZE,
        'playlist_count': None,
        'playlist_truncated': False,
    }


def inspect_url(url, media_type='video'):
    key = (url, media_type)
    cached = inspect_cache.get(key)
    if cached is not None:
        return cached
    try:
        result = _inspect(url, media_type)
    except Exception as exc:
        result = {'error': f'Erro inesperado ao analisar o URL: {exc}'}
    inspect_cache.put(key, result)
    return result


def build_download_options(job_dir, media_type, quality, progress_cb, message_cb):
    if media_type == 'video':
        if quality == 'best':
            fmt = 'bv*+ba/b'
        else:
            try:
                h = int(quality)
            except (TypeError, ValueError):
                h = 0
            if h > 0:
                fmt = (
                    f'bv*[height<={h}][ext=mp4]+ba[ext=m4a]/'
                    f'b[height<={h}][ext=mp4]/b[height<={h}]/'
                    f'bv*[height<={h}]+ba/b'
                )
            else:
                fmt = 'bv*+ba/b'
    else:
        fmt = 'bestaudio/best'

    opts = {
        'format': fmt,
        'outtmpl': {
            'default': os.path.join(job_dir, '%(title).80B [%(id)s].%(ext)s')
        },
        'merge_output_format': 'mp4',
        'noplaylist': False,
        'playlistend': config.MAX_PLAYLIST_ITEMS,
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
        'concurrent_fragment_downloads': 4,
        'continuedl': True,
        'progress_hooks': [progress_cb],
        'logger': _Logger(message_cb),
    }

    if media_type == 'audio':
        opts.pop('merge_output_format', None)
        postprocessors = []
        if quality == 'best':
            postprocessors.append({'key': 'FFmpegExtractAudio', 'preferredcodec': 'best'})
        else:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': AUDIO_QUALITY_MAP.get(quality),
            })
        opts['postprocessors'] = postprocessors

    return opts


def _is_artifact(name):
    return not (
        name.endswith('.part')
        or name.endswith('.ytdl')
        or '.orig.' in name
    )


def run_download(job_dir, url, media_type, quality, progress_cb, message_cb):
    opts = build_download_options(job_dir, media_type, quality, progress_cb, message_cb)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    files = sorted(
        f for f in os.listdir(job_dir)
        if os.path.isfile(os.path.join(job_dir, f)) and _is_artifact(f)
    )
    return files
