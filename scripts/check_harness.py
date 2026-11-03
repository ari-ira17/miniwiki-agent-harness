#!/usr/bin/env python3
"""Check MiniWiki harness structure without third-party dependencies.

Supported skill frontmatter uses single-line YAML scalars for name and
description. The local-only switch is an intermediate check, not final acceptance.
Report artifacts are local; use --with-report to require their evidence registry.
"""
import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

LOCAL = ("add-wiki-endpoint", "security-review", "session-handoff")
EXTERNAL = ("webapp-testing", "systematic-debugging", "grill-with-docs")
RULES = ("stack.md", "security.md", "workflow.md", "definition-of-done.md")
MEMORY = ("PROJECT.md", "PROGRESS.md", "DECISIONS.md", "GOTCHAS.md")
REQUIRED = ("AGENTS.md", "ROADMAP.md", "docs/requirements/ASSIGNMENT.md",
            "docs/architecture/HARNESS.md")
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def scalar(value):
    """Parse a conservative YAML scalar subset and reject ambiguous syntax."""
    value = value.strip()
    if not value:
        raise ValueError("empty scalar")
    if value[0] in "\"'":
        quote = value[0]
        if len(value) < 2 or value[-1] != quote:
            raise ValueError("unterminated quoted scalar")
        inner = value[1:-1]
        if quote == "'":
            if re.search(r"(?<!')'(?!')", inner):
                raise ValueError("invalid single-quoted scalar")
            return inner.replace("''", "'")
        # Quoted descriptions in this project do not need YAML escapes.
        if '"' in inner or "\\" in inner:
            raise ValueError("unsupported double-quoted scalar escape")
        return inner
    if re.search(r":(?:\s|$)|\s#", value) or value[0] in "[{&*!|>@`%":
        raise ValueError("unsupported or invalid plain scalar")
    if value in ("null", "~", "true", "false"):
        raise ValueError("expected a string scalar")
    return value


def check_skill(root, skill, errors):
    path = root / ".agents" / "skills" / skill / "SKILL.md"
    if not path.is_file():
        errors.append(f"missing {path.relative_to(root)}")
        return False
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {path}: {exc}")
        return False
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        errors.append(f"{skill}: missing YAML frontmatter delimiters")
        return False
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if match:
            key = match.group(1)
            if key in fields:
                errors.append(f"{skill}: duplicate {key}")
            try:
                fields[key] = scalar(match.group(2))
            except ValueError as exc:
                errors.append(f"{skill}: invalid {key}: {exc}")
        elif line and not line.startswith((" ", "#")):
            errors.append(f"{skill}: unsupported frontmatter line: {line}")
    name = fields.get("name", "")
    description = fields.get("description", "").strip()
    if not NAME.fullmatch(name) or len(name) > 64 or name != skill:
        errors.append(f"{skill}: invalid name or directory mismatch")
    if not description or len(description) > 1024:
        errors.append(f"{skill}: description must contain 1–1024 characters")
    if len(lines[end + 1:]) > 500:
        errors.append(f"{skill}: body exceeds recommended 500 lines")
    if not "\n".join(lines[end + 1:]).strip():
        errors.append(f"{skill}: empty body")
    for target in LINK.findall("\n".join(lines[end + 1:])):
        parsed = urlsplit(target.strip().split()[0])
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        resolved = (path.parent / unquote(parsed.path)).resolve()
        if not resolved.exists():
            errors.append(f"{skill}: broken relative link {target}")
    return any((path.parent / folder).is_dir() and
               any(item.is_file() for item in (path.parent / folder).rglob("*"))
               for folder in ("scripts", "references"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true",
                        help="intermediate validation of the three local skills")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="project root (also useful for isolated fixtures)")
    parser.add_argument("--with-report", action="store_true",
                        help="also require the local, Git-ignored report evidence registry")
    args = parser.parse_args()
    root = args.root.resolve()
    errors = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f"missing {name}")
    if args.with_report and not (root / "docs/report/evidence.md").is_file():
        errors.append("missing docs/report/evidence.md")
    for directory, names in (("docs/rules", RULES), ("docs/ai", MEMORY)):
        for name in names:
            if not (root / directory / name).is_file():
                errors.append(f"missing {directory}/{name}")
    agents = root / "AGENTS.md"
    if agents.is_file():
        contents = agents.read_text(encoding="utf-8")
        for name in RULES + MEMORY:
            if name not in contents:
                errors.append(f"AGENTS.md does not reference {name}")
    project = root / "docs/ai/PROJECT.md"
    if project.is_file() and len(project.read_text(encoding="utf-8").splitlines()) > 100:
        errors.append("docs/ai/PROJECT.md exceeds 100 lines")
    names = LOCAL if args.local_only else LOCAL + EXTERNAL
    resources = sum(check_skill(root, name, errors) for name in names)
    if resources < 2:
        errors.append("fewer than two skills have nonempty scripts/ or references/")
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        print(f"FAIL: {len(errors)} issue(s)", file=sys.stderr)
        return 1
    mode = "local-only (intermediate, not final acceptance)" if args.local_only else "full"
    report = "checked" if args.with_report else "not requested (use --with-report)"
    print(f"PASS: {mode}; {len(names)} skills; {resources} with resources; report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
