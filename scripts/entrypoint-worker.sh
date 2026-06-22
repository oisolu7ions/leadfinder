#!/bin/sh
# Background worker: wait for dependencies, process job queue.
set -eu

cd /app

echo "entrypoint_worker_starting"
python scripts/wait_for_dependencies.py

echo "starting_worker"
exec python -m app.workers.worker
