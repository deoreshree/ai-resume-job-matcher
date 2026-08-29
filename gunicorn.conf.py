"""Gunicorn configuration for production deployments of AI Resume Job Matcher."""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', 5000)}"
backlog = 2048

# Worker processes
workers = max(2, multiprocessing.cpu_count())
worker_class = "gthread"
threads = 2
worker_connections = 1000
timeout = 30
keepalive = 2

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = "/dev/shm"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "ai-resume-job-matcher"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("AI Resume & Job Match Predictor server is ready. Spawning workers.")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Shutting down.")
