from __future__ import annotations

import re
from dataclasses import dataclass

from .utils import normalize_text


@dataclass(frozen=True)
class ClassificationResult:
    is_supported: bool
    score: int
    reasons: list[str]


def classify_document(ocr_text: str) -> ClassificationResult:
    """
    Determine whether the OCR text looks like the expected invoice format.

    This is intentionally conservative. We want to reject unrelated documents,
    but still allow OCR noise in supported invoices.
    """
    text = normalize_text(ocr_text)
    lower = text.lower()

    checks = {
        "invoice_marker": bool(re.search(r"\binvoice\b|\binv(?:oice)?\.?\s*(?:no|#|number)", lower)),
        "invoice_number": bool(re.search(r"invoice\s*(?:number|no\.?|#)|inv\s*(?:number|no\.?|#)", lower)),
        "bill_to": bool(re.search(r"bill\s*to|billed\s*to|customer|client", lower)),
        "date": bool(re.search(r"\bdate\b|invoice\s*date", lower)),
        "line_header_sku": bool(re.search(r"\bsku\b|\bitem\b|\bproduct\b|\bcode\b", lower)),
        "line_header_description": bool(re.search(r"\bdescription\b|\bitem description\b", lower)),
        "line_header_quantity": bool(re.search(r"\bqty\b|\bquantity\b", lower)),
        "line_header_price_total": bool(re.search(r"\bprice\b|\bunit price\b|\brate\b", lower))
        and bool(re.search(r"\btotal\b|\bamount\b", lower)),
    }

    reasons = [name for name, passed in checks.items() if passed]
    score = len(reasons)

    # Require a strong invoice signal and enough table/header structure.
    is_supported = (
        checks["invoice_marker"]
        and checks["bill_to"]
        and checks["line_header_price_total"]
        and score >= 5
    )

    return ClassificationResult(
        is_supported=is_supported,
        score=score,
        reasons=reasons,
    )