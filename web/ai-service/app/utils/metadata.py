"""Metadata normalization helpers used by all loaders.

Loaders produce raw metadata dicts from file-format-specific APIs.
These helpers ensure the dict stored on the Document is always
clean, JSON-serializable, and compact.
"""
from typing import Any


def clean_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip None/empty values and convert non-serializable types to str.

    Lists are preserved (with element-level cleaning). Nested dicts are
    cleaned recursively. Unknown types are stringified so the API never
    returns a 500 due to a serialization error.
    """
    result: dict[str, Any] = {}
    for key, value in raw.items():
        cleaned = _clean_value(value)
        if cleaned is not None:
            result[key] = cleaned
    return result


def _clean_value(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    if isinstance(value, list):
        cleaned = [_clean_value(v) for v in value]
        return [v for v in cleaned if v is not None]
    if isinstance(value, dict):
        nested = clean_metadata(value)
        return nested if nested else None
    return str(value)
