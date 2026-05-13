from __future__ import annotations

from dataclasses import asdict

from .document_classifier import classify_document
from .switch_invoice_parser import SwitchInvoiceParser
from .utils import normalize_text


class InvoiceParser:
    def __init__(self, ocr_text: str):
        self.text = normalize_text(ocr_text)

    def parse(self, file_name: str | None = None) -> dict:
        classification = classify_document(self.text)

        if classification.is_supported and classification.document_type == "switch_invoice":
            return SwitchInvoiceParser(self.text).parse(file_name=file_name)

        return {
            "status": "rejected",
            "file_name": file_name,
            "reason": classification.reason,
            "classification": asdict(classification),
        }