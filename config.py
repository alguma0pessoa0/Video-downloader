import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', os.path.join(BASE_DIR, 'downloads'))

FILE_TTL = int(os.environ.get('FILE_TTL', 600))
CLEANUP_INTERVAL = int(os.environ.get('CLEANUP_INTERVAL', 60))
MAX_CONCURRENT_JOBS = int(os.environ.get('MAX_CONCURRENT_JOBS', 3))
MAX_PLAYLIST_ITEMS = int(os.environ.get('MAX_PLAYLIST_ITEMS', 50))
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 2 * 1024 * 1024 * 1024))
INSPECT_TIMEOUT = int(os.environ.get('INSPECT_TIMEOUT', 30))
DOWNLOAD_TIMEOUT = int(os.environ.get('DOWNLOAD_TIMEOUT', 3600))

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5000))

RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 60))
RATE_LIMIT_MAX = int(os.environ.get('RATE_LIMIT_MAX', 20))

SITES_FETCH_URL = os.environ.get(
    'SITES_FETCH_URL',
    'https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/supportedsites.md',
)
SITES_DESC_CACHE_TTL = int(os.environ.get('SITES_DESC_CACHE_TTL', 86400))
