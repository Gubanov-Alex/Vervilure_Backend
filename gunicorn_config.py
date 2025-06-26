import multiprocessing

bind = "127.0.0.1:8000"
workers = 2  # Для 1 CPU дроплета
worker_class = "sync"
worker_connections = 100
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
threads = 2
