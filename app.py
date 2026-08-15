import os
import threading
import time

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

import config
import downloader
import jobs
import supported_sites

app = Flask(__name__)

os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
jobs.start_janitor()


@app.after_request
def add_cors_headers(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return resp


@app.context_processor
def inject_globals():
    return {
        'max_playlist_items': config.MAX_PLAYLIST_ITEMS,
        'file_ttl_minutes': config.FILE_TTL // 60,
    }


class RateLimiter:
    def __init__(self, window, max_hits):
        self.window = window
        self.max = max_hits
        self._hits = {}
        self._lock = threading.Lock()

    def allow(self, key):
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self.window]
            if len(hits) >= self.max:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


rate_limiter = RateLimiter(config.RATE_LIMIT_WINDOW, config.RATE_LIMIT_MAX)


def client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _parse_body():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    media_type = data.get('media_type') or 'video'
    quality = (data.get('quality') or 'best').strip()
    if not url:
        return None, {'error': 'Informe um URL.'}, 400
    if media_type not in ('video', 'audio'):
        return None, {'error': 'Tipo inválido.'}, 400
    if quality not in (downloader.VIDEO_QUALITIES if media_type == 'video' else downloader.AUDIO_QUALITIES):
        return None, {'error': 'Qualidade inválida.'}, 400
    return {'url': url, 'media_type': media_type, 'quality': quality}, None, None


@app.get('/')
def index():
    return render_template('index.html')


@app.post('/inspect')
def inspect():
    if not rate_limiter.allow('inspect:' + client_ip()):
        return jsonify({'error': 'Muitas solicitações. Aguarde um pouco.'}), 429
    body, err, code = _parse_body()
    if err:
        return jsonify(err), code
    info = downloader.inspect_url(body['url'], body['media_type'])
    return jsonify(info)


@app.post('/download')
def download():
    if not rate_limiter.allow('download:' + client_ip()):
        return jsonify({'error': 'Muitas solicitações. Aguarde um pouco.'}), 429
    body, err, code = _parse_body()
    if err:
        return jsonify(err), code
    title = (request.get_json(silent=True) or {}).get('title') or 'Vídeo'
    job_id = jobs.manager.submit(body['url'], body['media_type'], body['quality'], title[:120])
    return jsonify({'job_id': job_id})


@app.get('/status/<job_id>')
def status(job_id):
    if not jobs.manager.get(job_id):
        abort(404)
    return render_template('status.html', job_id=job_id)


@app.get('/api/job/<job_id>')
def api_job(job_id):
    job = jobs.manager.get(job_id)
    if not job:
        return jsonify({'error': 'Job não encontrado'}), 404
    return jsonify(job.get_snapshot())


@app.get('/files/<job_id>')
def file_download(job_id):
    job = jobs.manager.get(job_id)
    if not job or not job.artifact:
        abort(404)
    path = os.path.join(job.dir, job.artifact)
    if not os.path.isfile(path):
        abort(404)
    return send_from_directory(
        job.dir,
        job.artifact,
        as_attachment=True,
        download_name=job.artifact,
        max_age=config.FILE_TTL,
    )


@app.get('/supported-sites')
def supported_sites_page():
    sites = supported_sites.get_site_list()
    broken = sum(1 for s in sites if s['working'] is False)
    return render_template('supported_sites.html', sites=sites, count=len(sites), broken=broken)


if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, threaded=True, debug=False)
