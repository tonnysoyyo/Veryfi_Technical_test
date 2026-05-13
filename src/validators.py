from __future__ import annotations

import math
import re
from numbers import Number


REQUIRED_ACCEPTED_KEYS = [
    "status",
    "document_type",
    "file_name",
    "vendor_name",
    "vendor_address",
    "bill_to_name",
    "invoice_number",
    "date",
    "line_items",
]

REQUIRED_LINE_ITEM_KEYS = [
    "sku",
    "description",
    "quantity",
    "tax_rate",
    "price",
    "total",
]


def validate_invoice_json(data: dict) -> list[str]:
    """
    Validate the final JSON produced by the parser.

    Important assumptions:
    - SKU is allowed to be None because the Switch invoice table has no SKU column.
    - tax_rate is allowed to be None because the Switch invoice table has no tax-rate column.
    - Negative prices/totals are allowed because discounts or credits can appear as negative line items.
    """
    warnings = []

    status = data.get("status")

    if status not in {"accepted", "rejected"}:
        warnings.append("Invalid or missing status. Expected 'accepted' or 'rejected'.")
        return warnings

    if status == "rejected":
        if not data.get("reason"):
            warnings.append("Rejected document is missing a rejection reason.")
        return warnings

    # Accepted document validation
    for key in REQUIRED_ACCEPTED_KEYS:
        if key not in data:
            warnings.append(f"Missing top-level key: {key}")

    for field in [
        "vendor_name",
        "vendor_address",
        "bill_to_name",
        "invoice_number",
        "date",
    ]:
        if not data.get(field):
            warnings.append(f"Missing or empty field: {field}")

    if data.get("vendor_name") != "Switch":
        warnings.append("vendor_name is expected to be 'Switch' for Switch invoices.")

    if data.get("document_type") != "switch_invoice":
        warnings.append("document_type is expected to be 'switch_invoice'.")

    date_value = data.get("date")
    if date_value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date_value)):
        warnings.append(f"Date is not in ISO format YYYY-MM-DD: {date_value}")

    line_items = data.get("line_items")

    if not isinstance(line_items, list):
        warnings.append("line_items must be a list.")
        return warnings

    if len(line_items) == 0:
        warnings.append("No line items were extracted.")
        return warnings

    for idx, item in enumerate(line_items, start=1):
        validate_line_item(item, idx, warnings)

    return warnings


def validate_line_item(item: dict, idx: int, warnings: list[str]) -> None:
    for key in REQUIRED_LINE_ITEM_KEYS:
        if key not in item:
            warnings.append(f"Line item {idx} missing key: {key}")

    description = item.get("description")
    if not isinstance(description, str) or not description.strip():
        warnings.append(f"Line item {idx} has missing or empty description.")

    # Switch invoices do not provide SKU or tax_rate.
    # Therefore, None is valid for these fields.
    sku = item.get("sku")
    if sku is not None and not isinstance(sku, str):
        warnings.append(f"Line item {idx} sku should be a string or null.")

    tax_rate = item.get("tax_rate")
    if tax_rate is not None and not isinstance(tax_rate, Number):
        warnings.append(f"Line item {idx} tax_rate should be numeric or null.")

    quantity = item.get("quantity")
    price = item.get("price")
    total = item.get("total")

    if not is_number(quantity):
        warnings.append(f"Line item {idx} quantity must be numeric.")

    if not is_number(price):
        warnings.append(f"Line item {idx} price must be numeric.")

    if not is_number(total):
        warnings.append(f"Line item {idx} total must be numeric.")

    # Negative prices/totals are allowed because discounts exist.
    if is_number(quantity) and is_number(price) and is_number(total):
        expected_total = quantity * price

        if not math.isclose(expected_total, total, abs_tol=0.05):
            warnings.append(
                f"Line item {idx} total may not match quantity * price. "
                f"quantity={quantity}, price={price}, total={total}, "
                f"expected={expected_total:.2f}"
            )


def is_number(value) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)