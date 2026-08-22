"""Conservative Gunicorn settings for the initial AWS t3.micro Alpha."""
import os

bind = os.getenv("TOTALRO_GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.getenv("TOTALRO_GUNICORN_WORKERS", "1"))
worker_class = "gthread"
threads = int(os.getenv("TOTALRO_GUNICORN_THREADS", "2"))
timeout = int(os.getenv("TOTALRO_GUNICORN_TIMEOUT", "600"))
graceful_timeout = 60
keepalive = 5
max_requests = 200
max_requests_jitter = 30
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("TOTALRO_LOG_LEVEL", "info")
capture_output = True
preload_app = False
