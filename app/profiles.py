"""Validation helpers for required account profile names."""

import unicodedata


def validate_person_name(value: str) -> str:
    """Reject control characters in a name after schema whitespace trimming."""
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError("Profile names cannot contain control characters.")
    return value
