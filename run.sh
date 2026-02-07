#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "$1" in
  test)
    PYTHONPATH="$ROOT_DIR:$PYTHONPATH" uv run pytest tests/ -v
    ;;
  serve)
    uv run python -m uvicorn src.main:app --reload
    ;;
  *)
    echo "Usage: $0 {test|serve}"
    exit 1
    ;;
esac
