# Deployment

## Local (recommended for now)

```bash
ollama serve
streamlit run main.py
```

This is a single-user, local-first app (no auth layer — see
[SECURITY.md](../SECURITY.md)), so local/LAN use is the intended default.

## Docker

The `Dockerfile` packages the Streamlit app itself. **Ollama is not
containerized** — it runs on the host and the container talks to it over
the network, the same way you'd point any client at a local LLM server.

```bash
docker build -t avia-ai .
```

**macOS / Windows** (Docker Desktop exposes the host via
`host.docker.internal`):

```bash
docker run -p 8501:8501 \
  --env-file .env \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  avia-ai
```

**Linux** (simplest: share the host network so `localhost:11434` inside
the container reaches Ollama on the host):

```bash
docker run --network host --env-file .env avia-ai
```

Make sure `ollama serve` is running on the host before starting the
container either way.

## Environment

All configuration is env-driven (`app/config.py` / `.env.example`) — no
secrets are baked into the image. Mount or pass `.env` at run time, never
`COPY` it into the Docker image.

## Notes for a real production deployment

This project hasn't been hardened for multi-tenant/public deployment.
Before deploying it beyond local/LAN use, you'd want to add at minimum:

- An authentication layer (there is none today)
- Per-session rate limiting on outbound API calls
- Persisting `app.agent.memory` / the LangGraph checkpointer to disk or a
  database instead of in-process `MemorySaver` (state is lost on restart
  and isn't shared across multiple app instances)
- A production ASGI/WSGI front (Streamlit's built-in server is fine for
  local/internal use, less so for public internet-facing traffic)
