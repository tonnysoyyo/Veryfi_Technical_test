from .document_classifier import classify_document
from .switch_invoice_parser import SwitchInvoiceParser, is_switch_invoice_format


class InvoiceParser:
    def __init__(self, ocr_text: str):
        self.text = ocr_text

    def parse(self, file_name: str | None = None) -> dict:
        if is_switch_invoice_format(self.text):
            return SwitchInvoiceParser(self.text).parse(file_name=file_name)

        classification = classify_document(self.text)

        return {
            "status": "rejected",
            "file_name": file_name,
            "reason": "Document does not match the expected Switch invoice format.",
            "classification": {
                "score": classification.score,
                "matched_rules": classification.reasons,
            },
        }