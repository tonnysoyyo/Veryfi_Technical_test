from src.switch_invoice_parser import SwitchInvoiceParser


def test_switch_parser_extracts_header_fields(switch_ocr_text):
    parser = SwitchInvoiceParser(switch_ocr_text)
    result = parser.parse(file_name="sample-switch.pdf")

    assert result["status"] == "accepted"
    assert result["document_type"] == "switch_invoice"
    assert result["file_name"] == "sample-switch.pdf"

    assert result["vendor_name"] == "Switch"
    assert result["vendor_address"] == "PO Box 674592, Dallas, TX 75267-4592"
    assert result["bill_to_name"] == "Toni Hackel"
    assert result["invoice_number"] == "1556267"
    assert result["date"] == "2023-09-22"


def test_switch_parser_extracts_line_items(switch_ocr_text):
    parser = SwitchInvoiceParser(switch_ocr_text)
    result = parser.parse(file_name="sample-switch.pdf")

    line_items = result["line_items"]

    assert len(line_items) == 4

    first_item = line_items[0]

    assert first_item["sku"] is None
    assert first_item["tax_rate"] is None
    assert first_item["description"] == (
        "Transport | Switch Fiber Pair (Intra-campus) | Pairs (4419693704) "
        "(04/2023|10 Gbps Fiber to HOEpyb (YSPG4VFH) (04/2023)"
    )
    assert first_item["quantity"] == 2912.98
    assert first_item["price"] == 934.09
    assert first_item["total"] == 2720985.49


def test_switch_parser_handles_multiline_descriptions_correctly(switch_ocr_text):
    parser = SwitchInvoiceParser(switch_ocr_text)
    result = parser.parse(file_name="sample-switch.pdf")

    second_item = result["line_items"][1]

    assert second_item["description"] == (
        "Carrier Taxes for Transport | 230 Gbps Wavelength Diverse between "
        "Sparks, OR 56789 and Plano, NV 98765 (SNpTfT) (NJYM5MQP) "
        "(07/2023 Taxes) (07/2023)"
    )
    assert second_item["quantity"] == 3500.87
    assert second_item["price"] == 6229.33
    assert second_item["total"] == 21808074.52


def test_switch_parser_allows_negative_discount_lines(switch_ocr_text):
    parser = SwitchInvoiceParser(switch_ocr_text)
    result = parser.parse(file_name="sample-switch.pdf")

    discount_item = result["line_items"][2]

    assert discount_item["description"] == "Special Partnership Discount (03/2023)"
    assert discount_item["quantity"] == 8.0
    assert discount_item["price"] == -561.0
    assert discount_item["total"] == -4488.0


def test_switch_parser_does_not_include_footer_in_line_items(switch_ocr_text):
    parser = SwitchInvoiceParser(switch_ocr_text)
    result = parser.parse(file_name="sample-switch.pdf")

    all_descriptions = " ".join(
        item["description"] for item in result["line_items"]
    ).lower()

    assert "total usd" not in all_descriptions
    assert "please update your system" not in all_descriptions
    assert "wire/ach payment" not in all_descriptions
    assert "www.switch.com" not in all_descriptions