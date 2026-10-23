"""
Gunicorn production configuration for Smart Civic System.
Ref: https://docs.gunicorn.org/en/stable/configure.html
"""
import os
import multiprocessing

# ── Binding ───────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# ── Workers ───────────────────────────────────────────────────────────────────
# Recommended formula: (2 × CPU cores) + 1
# Capped at 8 for memory-heavy ML workloads (OpenCV / numpy / YOLO)
workers = min(int(os.getenv("GUNICORN_WORKERS", (2 * multiprocessing.cpu_count()) + 1)), 8)
worker_class = "sync"          # sync workers; use "gevent" if you add async tasks
threads = int(os.getenv("GUNICORN_THREADS", "2"))

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))   # Allow time for YOLO inference
graceful_timeout = 30
keepalive = 5

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "logs/access.log")
errorlog  = os.getenv("GUNICORN_ERROR_LOG",  "logs/error.log")
loglevel  = os.getenv("GUNICORN_LOG_LEVEL",  "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ── Security ──────────────────────────────────────────────────────────────────
limit_request_line   = 8190
limit_request_fields = 100
forwarded_allow_ips  = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")

# ── Process naming ────────────────────────────────────────────────────────────
proc_name = "smartcivic"

# ── Pre-fork hook (warm-up) ───────────────────────────────────────────────────
def on_starting(server):
    import os
    os.makedirs("logs", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)
    server.log.info("SmartCivic Gunicorn starting up…")

def worker_exit(server, worker):
    server.log.info(f"Worker {worker.pid} exited.")
