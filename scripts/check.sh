#!/bin/sh
set -eu

mode="${1:-all}"
case "$mode" in
    all)
        docker compose exec app python -m pytest -q
        docker compose exec app ruff check .
        docker compose exec app ruff format --check .
        ;;
    test)
        docker compose exec app python -m pytest -q
        ;;
    lint)
        docker compose exec app ruff check .
        docker compose exec app ruff format --check .
        ;;
    smoke)
        python3 scripts/smoke.py
        ;;
    e2e)
        printf 'Browser workflows are not implemented yet.\n' >&2
        exit 2
        ;;
    *)
        printf 'Usage: %s [all|test|lint|smoke|e2e]\n' "$0" >&2
        exit 2
        ;;
esac
