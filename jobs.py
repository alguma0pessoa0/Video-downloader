import os
import threading
import time
import uuid
import zipfile

import config
import downloader


def _fmt_size(n):
    size = float(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024 or unit == 'TB':
            return f'{size:.1f} {unit}' if unit != 'B' else f'{int(size)} B'
        size /= 1024
    return f'{size:.1f} B'


def _make_zip(job_dir, files):
    zip_path = os.path.join(job_dir, 'download.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
        for f in files:
            zf.write(os.path.join(job_dir, f), arcname=f)
    return 'download.zip'


class Job:
    def __init__(self, job_id, url, media_type, quality, title):
        self.id = job_id
        self.url = url
        self.media_type = media_type
        self.quality = quality
        self.title = title
        self.state = 'queued'
        self.progress = 0
        self.message = 'Na fila...'
        self.files = []
        self.artifact = None
        self.error = None
        self.created_at = time.time()
        self.finished_at = None
        self.expires_at = None
        self.dir = os.path.join(config.DOWNLOAD_DIR, job_id)
        self._lock = threading.Lock()

    def set(self, **kw):
        with self._lock:
            for k, v in kw.items():
                setattr(self, k, v)

    def get_snapshot(self):
        with self._lock:
            return {
                'id': self.id,
                'state': self.state,
                'progress': round(self.progress),
                'message': self.message,
                'title': self.title,
                'media_type': self.media_type,
                'quality': self.quality,
                'files': list(self.files),
                'artifact': self.artifact,
                'error': self.error,
                'expires_in': int(self.expires_at - time.time()) if self.expires_at else None,
            }


class JobManager:
    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()
        self._sem = threading.BoundedSemaphore(config.MAX_CONCURRENT_JOBS)

    def submit(self, url, media_type, quality, title):
        job = Job(uuid.uuid4().hex, url, media_type, quality, title)
        os.makedirs(job.dir, exist_ok=True)
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(target=self._worker, args=(job,), daemon=True).start()
        return job.id

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def _worker(self, job):
        acquired = False
        try:
            self._sem.acquire()
            acquired = True
            job.set(state='downloading', message='Iniciando download...')

            def progress(d):
                status = d.get('status')
                if status == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    done = d.get('downloaded_bytes') or 0
                    info = d.get('info_dict') or {}
                    idx = info.get('playlist_index')
                    cnt = info.get('playlist_count')
                    label = f'item {idx}/{cnt} - ' if (idx and cnt) else ''
                    if total:
                        pct = min(95, done / total * 100)
                    else:
                        pct = job.progress or 0
                    speed = d.get('speed')
                    txt = f'Baixando {label}...'
                    if speed:
                        txt += f' ({_fmt_size(speed)}/s)'
                    job.set(progress=pct, message=txt)
                elif status == 'finished':
                    job.set(progress=95, message='Finalizando arquivo...')

            def msg_cb(text):
                job.set(message=text[-200:])

            files = downloader.run_download(
                job.dir, job.url, job.media_type, job.quality, progress, msg_cb
            )
            files = [f for f in files if not f.endswith(('.part', '.ytdl'))]

            if not files:
                job.set(state='error', error='Nenhum arquivo foi produzido.')
                return

            job.set(state='processing', message='Preparando arquivo...', files=files)
            if len(files) > 1:
                job.set(artifact=_make_zip(job.dir, files))
            else:
                job.set(artifact=files[0])

            job.set(
                state='ready',
                progress=100,
                message='Pronto!',
                finished_at=time.time(),
                expires_at=time.time() + config.FILE_TTL,
            )
        except Exception as exc:
            job.set(state='error', error=str(exc) or exc.__class__.__name__)
        finally:
            if acquired:
                self._sem.release()

    def run_janitor(self, stop_event):
        while not stop_event.is_set():
            stop_event.wait(config.CLEANUP_INTERVAL)
            self._cleanup()

    def _cleanup(self):
        root = config.DOWNLOAD_DIR
        now = time.time()
        try:
            if not os.path.isdir(root):
                return
            for name in os.listdir(root):
                path = os.path.join(root, name)
                if os.path.isdir(path):
                    self._cleanup_dir(path, name)
                elif os.path.isfile(path) and now - os.path.getmtime(path) > config.FILE_TTL:
                    self._remove(path)
        except Exception:
            pass

    def _cleanup_dir(self, path, name):
        now = time.time()
        with self._lock:
            job = self._jobs.get(name)
            if job and job.expires_at and now < job.expires_at:
                return
        try:
            for f in os.listdir(path):
                fpath = os.path.join(path, f)
                if now - os.path.getmtime(fpath) > config.FILE_TTL:
                    self._remove(fpath)
            if not os.listdir(path):
                os.rmdir(path)
                with self._lock:
                    self._jobs.pop(name, None)
        except OSError:
            pass

    @staticmethod
    def _remove(path):
        try:
            os.remove(path)
        except OSError:
            pass


manager = JobManager()


def start_janitor():
    stop = threading.Event()
    threading.Thread(target=manager.run_janitor, args=(stop,), daemon=True).start()
    return stop
