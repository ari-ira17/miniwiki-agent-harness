"""Canonical hierarchical page path validation tests."""

import pytest
from pydantic import ValidationError

from app.schemas.pages import PageCreate, validate_page_path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/",
        "docs/nlp",
        "/docs/nlp/",
        "/Docs/nlp",
        "/документы/nlp",
        "/docs//nlp",
        "/docs/./nlp",
        "/docs/../nlp",
        "/docs\\nlp",
        "/docs/my%2Fpath",
        "/docs/with space",
        "/docs/under_score",
        "/" + "a" * 65,
        "/" + "a" * 513,
    ],
)
def test_rejects_noncanonical_page_paths(path: str) -> None:
    with pytest.raises(ValueError):
        validate_page_path(path)


def test_accepts_nested_canonical_paths_without_normalizing() -> None:
    path = "/docs/nlp-101/unit2"
    assert validate_page_path(path) == path
    page = PageCreate(path=path, title="Course")
    assert page.path == path


def test_rejects_blank_title_and_oversized_markdown() -> None:
    with pytest.raises(ValidationError):
        PageCreate(path="/docs/nlp", title="  ")
    with pytest.raises(ValidationError):
        PageCreate(path="/docs/nlp", title="Course", markdown="x" * 200_001)
