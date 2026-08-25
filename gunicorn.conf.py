"""Conservative Gunicorn settings for the initial AWS t3.micro Alpha."""
import os

bind = os.getenv("TOTALRO_GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.getenv("TOTALRO_GUNICORN_WORKERS", "1"))
worker_class = "gthread"
threads = int(os.getenv("TOTALRO_GUNICORN_THREADS", "2"))
timeout = int(os.getenv("TOTALRO_GUNICORN_TIMEOUT", "600"))
graceful_timeout = 60
keepalive = 5
# Disable cumulative worker recycling. The browser status poll and long-running
# engineering requests can otherwise cross max_requests while a calculation is
# in flight, terminating the request before the replacement worker is ready.
# This setting takes effect only after the hosted service is redeployed/restarted.
max_requests = 0
max_requests_jitter = 0
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("TOTALRO_LOG_LEVEL", "info")
capture_output = True
preload_app = False
