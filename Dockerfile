# Avia AI — Streamlit app image.
#
# Ollama is NOT bundled here; it must run on the host (or another
# container) and be reachable via OLLAMA_BASE_URL. See docs/DEPLOYMENT.md.

FROM python:3.12-slim

WORKDIR /app

# System deps for faster-whisper's audio decoding (libsndfile) and healthcheck (curl).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY main.py ./
COPY .streamlit/ ./.streamlit/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
