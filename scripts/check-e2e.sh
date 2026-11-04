#!/bin/sh
set -eu

project="miniwiki-e2e-$$"

compose() {
    docker compose -p "$project" -f compose.yaml -f compose.e2e.yaml "$@"
}

cleanup() {
    compose down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM
compose up -d --build --wait
compose exec -T app python -m playwright install --with-deps chromium
compose exec -T app python -m app.demo
compose exec -T app python -m pytest -q -m e2e tests/e2e
mkdir -p docs/report/screenshots
compose cp app:/tmp/miniwiki-navigation-search.png docs/report/screenshots/05-navigation-01-search-tags-tree.png
compose cp app:/tmp/miniwiki-navigation-tag-filter.png docs/report/screenshots/05-navigation-06-tag-filter.png
compose cp app:/tmp/miniwiki-navigation-article.png docs/report/screenshots/05-navigation-02-article-toc.png
compose cp app:/tmp/miniwiki-navigation-empty.png docs/report/screenshots/05-navigation-03-empty-search.png
compose cp app:/tmp/miniwiki-navigation-mobile.png docs/report/screenshots/05-navigation-04-mobile.png
