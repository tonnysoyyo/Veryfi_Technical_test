from src.invoice_parser import InvoiceParser


def test_invoice_parser_routes_switch_invoice_to_switch_parser(switch_ocr_text):
    parser = InvoiceParser(switch_ocr_text)
    result = parser.parse(file_name="sample-switch.pdf")

    assert result["status"] == "accepted"
    assert result["document_type"] == "switch_invoice"
    assert result["vendor_name"] == "Switch"
    assert result["invoice_number"] == "1556267"
    assert len(result["line_items"]) == 4


def test_invoice_parser_rejects_unsupported_document(unsupported_text):
    parser = InvoiceParser(unsupported_text)
    result = parser.parse(file_name="unsupported.txt")

    assert result["status"] == "rejected"
    assert result["file_name"] == "unsupported.txt"
    assert "reason" in result
    assert result["classification"]["is_supported"] is False