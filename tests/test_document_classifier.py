from src.document_classifier import classify_document


def test_switch_invoice_is_supported(switch_ocr_text):
    result = classify_document(switch_ocr_text)

    assert result.is_supported is True
    assert result.document_type == "switch_invoice"
    assert result.score >= 7
    assert "switch" in result.matched_markers
    assert "description" in result.matched_markers
    assert "quantity" in result.matched_markers
    assert "rate" in result.matched_markers
    assert "amount" in result.matched_markers


def test_unsupported_document_is_rejected(unsupported_text):
    result = classify_document(unsupported_text)

    assert result.is_supported is False
    assert result.document_type is None
    assert "does not match" in result.reason.lower()