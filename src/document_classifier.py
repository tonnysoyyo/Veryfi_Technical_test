from __future__ import annotations

from dataclasses import dataclass

from .utils import normalize_text


@dataclass(frozen=True)
class ClassificationResult:
    is_supported: bool
    document_type: str | None
    score: int
    matched_markers: list[str]
    missing_markers: list[str]
    reason: str


SWITCH_REQUIRED_MARKERS = [
    "switch",
    "invoice date",
    "due date",
    "invoice no",
    "account no",
    "p.o. number",
    "description",
    "quantity",
    "rate",
    "amount",
]


def classify_document(ocr_text: str) -> ClassificationResult:
    """
    Classify whether a document belongs to the expected Switch invoice format.

    Since the provided PDFs follow the Switch invoice template, this classifier 
    is intentionally template-specific.
    """
    text = normalize_text(ocr_text).lower()

    matched_markers = [
        marker for marker in SWITCH_REQUIRED_MARKERS
        if marker in text
    ]

    missing_markers = [
        marker for marker in SWITCH_REQUIRED_MARKERS
        if marker not in text
    ]

    score = len(matched_markers)

    # All markers are not requiredbecause OCR can introduce small errors.
    # However, the document must have a strong Switch invoice signature.
    is_supported = (
        "switch" in matched_markers
        and "description" in matched_markers
        and "quantity" in matched_markers
        and "rate" in matched_markers
        and "amount" in matched_markers
        and score >= 7
    )

    if is_supported:
        return ClassificationResult(
            is_supported=True,
            document_type="switch_invoice",
            score=score,
            matched_markers=matched_markers,
            missing_markers=missing_markers,
            reason="Document matches the expected Switch invoice format.",
        )

    return ClassificationResult(
        is_supported=False,
        document_type=None,
        score=score,
        matched_markers=matched_markers,
        missing_markers=missing_markers,
        reason="Document does not match the expected Switch invoice format.",
    )