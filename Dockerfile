FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py config.py downloader.py jobs.py supported_sites.py ./
COPY templates ./templates
COPY sites_desc.json ./

EXPOSE 8000

CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=${PORT:-8000} --threads=4 app:app"]
