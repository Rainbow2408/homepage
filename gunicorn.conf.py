# gunicorn.conf.py
# Gunicorn production configuration for Render deployment

# ── Workers ──────────────────────────────────────────────────────────────────
# Use threaded workers so one slow OpenAI request doesn't block other requests
worker_class = "gthread"
workers = 2
threads = 4

# ── Timeout ───────────────────────────────────────────────────────────────────
# OpenAI image generation (DALL-E / gpt-image-1) can take 30–90 seconds.
# Default Gunicorn timeout is 30s which is too short — increase to 120s.
timeout = 120

# Keep-alive connections
keepalive = 5

# ── Logging ──────────────────────────────────────────────────────────────────
accesslog = "-"   # stdout
errorlog  = "-"   # stderr
loglevel  = "info"
