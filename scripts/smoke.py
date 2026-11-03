#!/usr/bin/env python3
"""Exercise local Compose readiness and persistence without deleting volumes."""

from __future__ import annotations

import json
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

COMPOSE = ["docker", "compose"]
HEALTH_URL = "http://127.0.0.1:8000/health"
SNAPSHOT_CODE = """
import json
from sqlalchemy import select
from app.db import get_session_factory
from app.models.user import User
with get_session_factory()() as session:
    users = session.scalars(select(User).order_by(User.id)).all()
    print(json.dumps([
        [u.id, u.username, u.role.value, u.is_active, u.password_hash]
        for u in users
    ]))
"""


def compose(*args: str) -> None:
    subprocess.run([*COMPOSE, *args], check=True)


def health() -> tuple[int, dict]:
    try:
        with urlopen(HEALTH_URL, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def wait_ready() -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            if health() == (200, {"status": "ok"}):
                return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(1)
    raise RuntimeError("Health did not become ready within 45 seconds")


def user_snapshot() -> list:
    # Credentials and password hashes stay in memory, never in evidence output.
    result = subprocess.run(
        [*COMPOSE, "exec", "-T", "app", "python", "-c", SNAPSHOT_CODE],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main() -> None:
    compose("up", "--build", "-d", "--wait")
    wait_ready()
    before = user_snapshot()
    admins = [u for u in before if u[2] == "admin" and u[3]]
    if len(admins) != 1 or not admins[0][4].startswith("$argon2id$"):
        raise RuntimeError("Expected exactly one active Argon2 bootstrap admin")
    print("PASS: first startup, health200, one active Argon2 admin", flush=True)

    compose("exec", "-T", "app", "python", "-m", "app.bootstrap")
    if user_snapshot() != before:
        raise RuntimeError("Bootstrap changed existing accounts")
    print("PASS: repeated bootstrap preserves accounts and password hashes", flush=True)

    compose("down")  # Deliberately no --volumes: preserve the application data.
    compose("up", "--build", "-d", "--wait")
    wait_ready()
    if user_snapshot() != before:
        raise RuntimeError("Data changed after container recreation")
    print("PASS: down/up preserves account IDs, roles and password hashes", flush=True)

    try:
        compose("stop", "db")
        if health() != (503, {"status": "unavailable"}):
            raise RuntimeError("Database outage did not produce generic health503")
        print("PASS: database outage returns generic health503", flush=True)
    finally:
        compose("start", "db")
        wait_ready()
    print("PASS: database recovery restores health200", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (
        subprocess.CalledProcessError,
        RuntimeError,
        URLError,
        ConnectionError,
        ValueError,
    ) as error:
        # Avoid printing subprocess output: it may contain connection internals.
        print(f"FAIL: Compose smoke check ({type(error).__name__})", flush=True)
        raise SystemExit(1) from None
