#!/bin/sh
# Scheduler: wait for dependencies, run scheduled task loop.
set -eu

cd /app

echo "entrypoint_scheduler_starting"
python scripts/wait_for_dependencies.py

echo "starting_scheduler"
exec python -m app.scheduler.runner
