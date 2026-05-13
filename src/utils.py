from __future__ import annotations

import re
from datetime import date
from typing import Optional
from dateutil import parser as date_parser


def normalize_text(text: str) -> str:
    """
    Normalize OCR text while preserving line boundaries.
    """
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in normalize_text(text).split("\n") if line.strip()]


def normalize_date(value: str | None) -> Optional[str]:
    """
    Parse a date string and return ISO format YYYY-MM-DD.
    """
    if value is None:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        parsed = date_parser.parse(value, fuzzy=True, dayfirst=False)
        return parsed.date().isoformat()
    except (ValueError, OverflowError):
        return None


def slugify_filename(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_") or "document"