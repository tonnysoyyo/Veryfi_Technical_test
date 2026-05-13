from src.invoice_parser import InvoiceParser
from src.validators import validate_invoice_json


def test_validator_accepts_valid_switch_invoice(switch_ocr_text):
    result = InvoiceParser(switch_ocr_text).parse(file_name="sample-switch.pdf")
    warnings = validate_invoice_json(result)

    assert warnings == []


def test_validator_allows_null_sku_and_tax_rate(switch_ocr_text):
    result = InvoiceParser(switch_ocr_text).parse(file_name="sample-switch.pdf")
    warnings = validate_invoice_json(result)

    for item in result["line_items"]:
        assert item["sku"] is None
        assert item["tax_rate"] is None

    assert warnings == []


def test_validator_allows_negative_prices_for_discounts(switch_ocr_text):
    result = InvoiceParser(switch_ocr_text).parse(file_name="sample-switch.pdf")
    warnings = validate_invoice_json(result)

    negative_items = [
        item for item in result["line_items"]
        if item["price"] < 0 or item["total"] < 0
    ]

    assert len(negative_items) >= 1
    assert warnings == []


def test_validator_rejected_document_with_reason_is_valid(unsupported_text):
    result = InvoiceParser(unsupported_text).parse(file_name="unsupported.txt")
    warnings = validate_invoice_json(result)

    assert result["status"] == "rejected"
    assert warnings == []