# MiniWiki

MiniWiki is a small, server-rendered wiki for the NLP course project. This
stage provides the FastAPI service, PostgreSQL, environment configuration,
database migrations, and a database-backed readiness endpoint.

## Requirements

- Docker Engine with Docker Compose v2
- A local `.env` file copied from `.env.example`

Set distinct local values for `POSTGRES_PASSWORD` and `ADMIN_PASSWORD` in
`.env`. Keep `.env` private; it is ignored by Git.
The initial administrator is prepared by the startup configuration, but login
and authorization are not implemented yet. Do not expose this development
service to an untrusted network.

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

`/health` returns `200 {"status":"ok"}` when a simple PostgreSQL query
succeeds, or a generic `503 {"status":"unavailable"}` while the database is
unavailable. It does not reveal connection details.

To stop services while preserving data, run `docker compose down`. To erase the
database volume explicitly, run `docker compose down --volumes`.

## Configuration

Copy `.env.example` to `.env`. `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` configure the application.
It constructs the database URL from individual PostgreSQL values so passwords
containing URL punctuation are escaped correctly. Login and authorization are
planned for a later stage; this prototype does not provide a secure access
system.

## Development checks

```sh
./scripts/check.sh
```

Browser end-to-end checks are reserved until those workflows are implemented.
After a first local startup, `python3 scripts/smoke.py` checks bootstrap
idempotence, health behavior, and data preservation across Compose restarts.
It stops and restarts the database container but never removes the named volume.
