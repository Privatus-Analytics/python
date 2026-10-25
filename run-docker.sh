#!/bin/sh
# Runs tests, Ruff and the package build in a pinned Python image. Usage: ./run-docker.sh
set -e
docker run --rm -v "$PWD":/app -w /app -e PIP_DISABLE_PIP_VERSION_CHECK=1 -e PIP_ROOT_USER_ACTION=ignore \
  -e RUFF_NO_CACHE=true -e PYTHONDONTWRITEBYTECODE=1 python:3.13-slim sh -c '
  set -e
  pip install --quiet ".[dev]"
  pytest
  ruff check .
  ruff format --check .
  python -m build --outdir /tmp/dist . >/dev/null 2>&1
  ls /tmp/dist
'
