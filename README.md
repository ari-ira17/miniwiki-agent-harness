# MiniWiki

MiniWiki is a small, server-rendered wiki for the NLP course project. It uses
FastAPI, PostgreSQL and migrations, and provides a page REST API plus a
Markdown editor with sanitized previews and articles. It supports case-
insensitive search, tags, a collapsible page tree and article outlines.
Article access requires login. Admins manage accounts; editors maintain articles;
readers can read only articles tagged `public`. Guests cannot read articles.

## Requirements

- Docker Engine with Docker Compose v2
- A local `.env` file copied from `.env.example`

Set distinct local values for `POSTGRES_PASSWORD` and `ADMIN_PASSWORD` in
`.env`. Keep `.env` private; it is ignored by Git.
The first administrator is created from the startup environment. Open `/login`
and sign in with those credentials. There is no self-registration; the admin
creates other users and assigns their roles. New account names are normalized
with trim/casefold; existing account names and passwords are preserved.

## Start

```sh
cp .env.example .env
# Edit .env and replace both placeholder passwords.
docker compose up --build
```

The app listens on `http://127.0.0.1:8000`. PostgreSQL is reachable by the app
inside the Compose network and is not published on the host. Its data lives in
the named `postgres_data` volume and survives container recreation and ordinary
`docker compose down`.

Check readiness:

```sh
curl --fail http://localhost:8000/health
docker compose exec app alembic current
docker compose exec app python -m pytest -q
docker compose exec app ruff check .
docker compose exec app ruff format --check .
```

Each app start creates an active administrator using `ADMIN_USERNAME` and
`ADMIN_PASSWORD` only when none exists. The password is stored as an Argon2
hash. Later starts leave existing users and passwords unchanged. If the
database has no active admin and the configured name belongs to an editor,
reader, or inactive admin, startup stops with a generic configuration error
rather than changing that account.

Both first and last names are required for user accounts. The initial admin
gets these names from `ADMIN_FIRST_NAME` and `ADMIN_LAST_NAME` in the local env.
Admins can open `/users` to create accounts, edit names, assign roles, disable users,
reset passwords or delete accounts. The final active admin is protected from
deletion, deactivation and demotion. Role/password changes revoke that user's
sessions. Removing a user preserves their articles. Users sign in with the
credentials supplied by the admin; the app does not deliver passwords.

`/health` returns `200 {"status":"ok"}` when a simple PostgreSQL query
succeeds, or a generic `503 {"status":"unavailable"}` while the database is
unavailable. It does not reveal connection details.

To stop services while preserving data, run `docker compose down`. To erase the
database volume explicitly, run `docker compose down --volumes`.

## Configuration

Copy `.env.example` to `.env`. `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_FIRST_NAME` and
`ADMIN_LAST_NAME` configure the application.
It constructs the database URL from individual PostgreSQL values so passwords
containing URL punctuation are escaped correctly. Server-side sessions expire
after eight hours. For HTTPS deployments enable Secure cookies using
`SESSION_COOKIE_SECURE=true`; the default local HTTP profile uses false.
State-changing API calls use session cookies and an `X-CSRF-Token`; see
[docs/api.md](docs/api.md) for the login flow.

## Development checks

After signing in, the discipline catalog opens. Admins and editors can click
**Создать страницу** in the header (or open `/pages/new`), enter an immutable
hierarchical path, title and Markdown, preview, then save. `/pages` remains
available for search and tag filtering. Add the `public` tag to make an
article readable by readers; removing it makes the article private.
The home page lists disciplines by year. NLP and the fifth-semester programming
workshop open local course articles; the other catalog links return home.
The NLP course links to a local preprocessing lecture. Course material links
return to their course, except for the specified CRISP-DM presentation.
Articles show tags and the last editor's full name and change time. The original
creator remains stored separately in the database/API and is not shown in the article.
The sidebar groups courses by degree and year. Each course has a main-page
link and a folder of local lectures. Empty
lecture folders show **Лекции отсутствуют**; document sections remain in the
article outline. A circular arrow at the bottom left hides or restores the
sidebar; the wider reading layout retains outer margins and a width limit.

To create only missing course articles and the preprocessing lecture, run
`docker compose exec app python -m app.course_samples`. Existing articles are
preserved on rerun; startup does not overwrite user content or delete pages.
`app.demo` supplies isolated test fixtures and is not needed in the working wiki.
REST contracts and examples are in [docs/api.md](docs/api.md) and `/docs`.

Markdown images use absolute HTTP(S) URLs; MiniWiki stores the link, not the
file. Uploads are outside the MVP; the planned export will preserve those links.

```sh
./scripts/check.sh
```

The default `all` mode runs unit/integration tests and Ruff. Browser E2E and
the restart smoke check are separate commands described below.

`./scripts/check.sh e2e` runs the browser editor, navigation and role scenarios in a separate Compose
project with an isolated PostgreSQL volume and no published host ports. It
installs Chromium and system libraries in that temporary app container, seeds
only missing demo pages, tests search, tags, navigation, preview, CRUD, admin
account creation, reader restrictions, login/logout and session revocation, then
removes the isolated containers and volume. It does not
use the regular local database or its pages. Forms require JavaScript for the
normal JSON workflow; without it they safely submit by POST and are rejected
without placing credentials in the URL.
After a first local startup, `python3 scripts/smoke.py` checks bootstrap
idempotence, health behavior, and data preservation across Compose restarts.
It stops and restarts the database container but never removes the named volume.

## Project harness and local report

Run `python3 scripts/check_harness.py` to validate the versioned rules, memory,
and skills. The whole `docs/report/` directory is local and Git-ignored; report
links in project notes refer to that local collection. It is not included in a
fresh clone. Keep a separate backup of report materials. Use
`python3 scripts/check_harness.py --with-report` to also require the local
evidence registry when preparing the report.

The UI uses Roboto Variable from Google Fonts (`ofl/roboto`), distributed
under the SIL Open Font License 1.1; see `app/static/fonts/OFL-Roboto.txt`.
