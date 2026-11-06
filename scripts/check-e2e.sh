#!/bin/sh
set -eu

project="miniwiki-e2e-$$"

compose() {
    docker compose -p "$project" -f compose.yaml -f - "$@" <<'YAML'
services:
  app:
    ports: !reset []
YAML
}

cleanup() {
    compose down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM
compose up -d --build --wait
compose exec -T app python -m playwright install --with-deps chromium
compose exec -T app python -m app.demo
compose exec -T app python -m app.course_samples
compose exec -T app python -m pytest -q -m e2e tests/e2e
mkdir -p docs/report/screenshots
compose cp app:/tmp/miniwiki-navigation-search.png docs/report/screenshots/06-profile-2-navigation-search.png
compose cp app:/tmp/miniwiki-navigation-tag-filter.png docs/report/screenshots/06-profile-2-navigation-tag-filter.png
compose cp app:/tmp/miniwiki-navigation-article.png docs/report/screenshots/06-profile-2-navigation-article-toc.png
compose cp app:/tmp/miniwiki-navigation-empty.png docs/report/screenshots/06-profile-2-navigation-empty-search.png
compose cp app:/tmp/miniwiki-navigation-mobile.png docs/report/screenshots/06-profile-2-navigation-mobile.png
compose cp app:/tmp/miniwiki-06-editor-preview.png docs/report/screenshots/06-profile-2-editor-preview.png
compose cp app:/tmp/miniwiki-06-editor-article.png docs/report/screenshots/06-profile-2-editor-article.png
compose cp app:/tmp/miniwiki-06-editor-mobile.png docs/report/screenshots/06-profile-2-editor-mobile.png
compose cp app:/tmp/miniwiki-06-login-desktop.png docs/report/screenshots/06-profile-2-login-desktop.png
compose cp app:/tmp/miniwiki-06-users-admin-desktop.png docs/report/screenshots/06-profile-2-users-admin-desktop.png
compose cp app:/tmp/miniwiki-06-users-admin-390.png docs/report/screenshots/06-profile-2-users-admin-390.png
compose cp app:/tmp/miniwiki-06-users-admin-320.png docs/report/screenshots/06-profile-2-users-admin-320.png
compose cp app:/tmp/miniwiki-06-role-editor.png docs/report/screenshots/06-profile-2-role-editor.png
compose cp app:/tmp/miniwiki-06-role-reader-desktop.png docs/report/screenshots/06-profile-2-role-reader-desktop.png
compose cp app:/tmp/miniwiki-06-role-reader-390.png docs/report/screenshots/06-profile-2-role-reader-390.png
compose cp app:/tmp/miniwiki-06-role-reader-320.png docs/report/screenshots/06-profile-2-role-reader-320.png
compose cp app:/tmp/miniwiki-profile2-home-desktop.png docs/report/screenshots/06-profile-2-home-desktop.png
compose cp app:/tmp/miniwiki-profile2-home-390.png docs/report/screenshots/06-profile-2-home-390.png
compose cp app:/tmp/miniwiki-profile2-home-320.png docs/report/screenshots/06-profile-2-home-320.png
compose cp app:/tmp/miniwiki-profile2-tree-collapsed.png docs/report/screenshots/06-profile-2-tree-collapsed.png
compose cp app:/tmp/miniwiki-profile2-preprocessing-desktop.png docs/report/screenshots/06-profile-2-preprocessing-desktop.png
compose cp app:/tmp/miniwiki-profile2-preprocessing-regex.png docs/report/screenshots/06-profile-2-preprocessing-regex.png
compose cp app:/tmp/miniwiki-profile2-preprocessing-bpe.png docs/report/screenshots/06-profile-2-preprocessing-bpe.png
compose cp app:/tmp/miniwiki-profile2-preprocessing-390.png docs/report/screenshots/06-profile-2-preprocessing-390.png
compose cp app:/tmp/miniwiki-profile2-preprocessing-320.png docs/report/screenshots/06-profile-2-preprocessing-320.png
compose cp app:/tmp/miniwiki-profile2-practice-desktop.png docs/report/screenshots/06-profile-2-practice-desktop.png
compose cp app:/tmp/miniwiki-07-export-download.png docs/report/screenshots/07-export-01-download.png
compose cp app:/tmp/miniwiki-07-export-archive.png docs/report/screenshots/07-export-02-archive.png
compose cp app:/tmp/miniwiki-07-api-openapi.png docs/report/screenshots/07-api-01-openapi.png
