from __future__ import annotations


def validate_invoice_json(data: dict) -> list[str]:
    """
    Return a list of validation warnings.
    """
    warnings = []

    if data.get("status") == "rejected":
        return warnings

    required_fields = [
        "vendor_name",
        "vendor_address",
        "bill_to_name",
        "invoice_number",
        "date",
        "line_items",
    ]

    for field in required_fields:
        if field not in data:
            warnings.append(f"Missing key: {field}")

    if not isinstance(data.get("line_items", []), list):
        warnings.append("line_items must be a list.")
        return warnings

    for idx, item in enumerate(data.get("line_items", []), start=1):
        for field in ["sku", "description", "quantity", "tax_rate", "price", "total"]:
            if field not in item:
                warnings.append(f"Line item {idx} missing key: {field}")

        if item.get("quantity") is not None and item["quantity"] < 0:
            warnings.append(f"Line item {idx} has negative quantity.")

        # if item.get("price") is not None and item["price"] < 0:
        #     warnings.append(f"Line item {idx} has negative price.")

    return warnings
