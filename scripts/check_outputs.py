from __future__ import annotations

import json
import math
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path("data/output")
OCR_DIR = Path("data/ocr")

EXPECTED_INVOICES = {
    "synth_switch_v5_4_labels.json": {
        "pdf_name": "synth-switch_v5-4.pdf",
        "bill_to_name": "Toni Hackel",
        "invoice_number": "1556267",
        "date": "2023-09-22",
        "line_items": 7,
        "invoice_total": Decimal("58164641.64"),
    },
    "synth_switch_v5_7_labels.json": {
        "pdf_name": "synth-switch_v5-7.pdf",
        "bill_to_name": "Nu Life Health",
        "invoice_number": "16005913",
        "date": "2023-09-11",
        "line_items": 6,
        "invoice_total": Decimal("46340224.75"),
    },
    "synth_switch_v5_14_labels.json": {
        "pdf_name": "synth-switch_v5-14.pdf",
        "bill_to_name": "Micro Merchant Systems, Inc.",
        "invoice_number": "055205954",
        "date": "2024-09-06",
        "line_items": 29,
        "invoice_total": Decimal("272677319.75"),
    },
    "synth_switch_v5_68_labels.json": {
        "pdf_name": "synth-switch_v5-68.pdf",
        "bill_to_name": "Dataiku, Inc.",
        "invoice_number": "699581195",
        "date": "2023-11-18",
        "line_items": 27,
        "invoice_total": Decimal("143773954.55"),
    },
    "synth_switch_v5_79_labels.json": {
        "pdf_name": "synth-switch_v5-79.pdf",
        "bill_to_name": "IncentX",
        "invoice_number": "9230090",
        "date": "2024-01-12",
        "line_items": 52,
        "invoice_total": Decimal("446704537.84"),
    },
}

REQUIRED_TOP_LEVEL_KEYS = {
    "status",
    "document_type",
    "file_name",
    "vendor_name",
    "vendor_address",
    "bill_to_name",
    "invoice_number",
    "date",
    "line_items",
    "warnings",
}

REQUIRED_LINE_ITEM_KEYS = {
    "sku",
    "description",
    "quantity",
    "tax_rate",
    "price",
    "total",
}

FORBIDDEN_DESCRIPTION_PATTERNS = [
    r"total\s+usd",
    r"\busd\s+\$",
    r"please update your system",
    r"please contact accounts",
    r"please make payments",
    r"wire/ach payment",
    r"ach routing",
    r"wire routing",
    r"swift",
    r"for questions",
    r"phone no",
    r"fax no",
    r"e-mail",
    r"web site",
    r"accountsreceivable@switch\.com",
    r"accounts receivable@switch\.com",
    r"www\.switch\.com",
    r"invoice date.*due date.*invoice no",
    r"account no.*p\.o\. number",
    r"description.*quantity.*rate.*amount",
    r"page\s+\d+\s+of\s+\d+",
    r"\b\d+\s+of\s+\d+\b",
    r"po box 674592",
    r"dallas,\s*tx\s*75267",
]

SUSPICIOUS_DESCRIPTION_PATTERNS = [
    r"\band\s*$",
    r"\bbetween\b.*\band\s*$",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise AssertionError(f"Missing file: {path}")
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Invalid JSON in {path}: {exc}") from exc


def to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise AssertionError(f"Value is not numeric: {value!r}")


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_required_keys(data: dict[str, Any], required: set[str], context: str, errors: list[str]) -> None:
    missing = required - set(data.keys())
    if missing:
        errors.append(f"{context}: missing keys: {sorted(missing)}")


def check_no_forbidden_description_text(
    file_name: str,
    item_idx: int,
    description: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    lower = description.lower()

    for pattern in FORBIDDEN_DESCRIPTION_PATTERNS:
        if re.search(pattern, lower, flags=re.IGNORECASE):
            errors.append(
                f"{file_name}: line item {item_idx} contains forbidden header/footer text: {pattern}"
            )

    for pattern in SUSPICIOUS_DESCRIPTION_PATTERNS:
        if re.search(pattern, lower, flags=re.IGNORECASE):
            warnings.append(
                f"{file_name}: line item {item_idx} description may be incomplete: {description}"
            )


def check_line_item(
    file_name: str,
    item: dict[str, Any],
    item_idx: int,
    errors: list[str],
    warnings: list[str],
) -> Decimal:
    context = f"{file_name}: line item {item_idx}"

    check_required_keys(item, REQUIRED_LINE_ITEM_KEYS, context, errors)

    description = item.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{context}: missing or empty description")
    else:
        check_no_forbidden_description_text(file_name, item_idx, description, errors, warnings)

    if item.get("sku") is not None:
        errors.append(f"{context}: sku should be null for this Switch invoice format")

    if item.get("tax_rate") is not None:
        errors.append(f"{context}: tax_rate should be null for this Switch invoice format")

    for field in ["quantity", "price", "total"]:
        if not is_number(item.get(field)):
            errors.append(f"{context}: {field} must be numeric")

    quantity = item.get("quantity")
    price = item.get("price")
    total = item.get("total")

    if is_number(quantity) and is_number(price) and is_number(total):
        expected_total = float(quantity) * float(price)

        if not math.isclose(expected_total, float(total), abs_tol=0.10, rel_tol=0.0001):
            warnings.append(
                f"{context}: quantity * price may not match total. "
                f"quantity={quantity}, price={price}, total={total}, expected={expected_total:.2f}"
            )

    return to_decimal(total) if is_number(total) else Decimal("0")


def check_invoice_output(
    output_file: str,
    expected: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    path = OUTPUT_DIR / output_file
    data = load_json(path)

    print(f"\nChecking {output_file}")
    print(f"  Invoice number: {data.get('invoice_number')}")
    print(f"  Bill to: {data.get('bill_to_name')}")
    print(f"  Date: {data.get('date')}")
    print(f"  Line items: {len(data.get('line_items', [])) if isinstance(data.get('line_items'), list) else 'INVALID'}")

    check_required_keys(data, REQUIRED_TOP_LEVEL_KEYS, output_file, errors)

    if data.get("status") != "accepted":
        errors.append(f"{output_file}: status should be accepted")

    if data.get("document_type") != "switch_invoice":
        errors.append(f"{output_file}: document_type should be switch_invoice")

    if data.get("file_name") != expected["pdf_name"]:
        errors.append(
            f"{output_file}: file_name mismatch. "
            f"Expected {expected['pdf_name']}, got {data.get('file_name')}"
        )

    if data.get("vendor_name") != "Switch":
        errors.append(f"{output_file}: vendor_name should be Switch")

    if data.get("vendor_address") != "PO Box 674592, Dallas, TX 75267-4592":
        errors.append(f"{output_file}: vendor_address is incorrect or incomplete")

    for field in ["bill_to_name", "invoice_number", "date"]:
        if data.get(field) != expected[field]:
            errors.append(
                f"{output_file}: {field} mismatch. "
                f"Expected {expected[field]!r}, got {data.get(field)!r}"
            )

    line_items = data.get("line_items")
    if not isinstance(line_items, list):
        errors.append(f"{output_file}: line_items must be a list")
        return

    if len(line_items) != expected["line_items"]:
        errors.append(
            f"{output_file}: expected {expected['line_items']} line items, "
            f"got {len(line_items)}"
        )

    total_sum = Decimal("0")

    for idx, item in enumerate(line_items, start=1):
        if not isinstance(item, dict):
            errors.append(f"{output_file}: line item {idx} must be an object")
            continue

        total_sum += check_line_item(output_file, item, idx, errors, warnings)

    expected_total = expected["invoice_total"]

    if total_sum.quantize(Decimal("0.01")) != expected_total:
        errors.append(
            f"{output_file}: line-item total sum mismatch. "
            f"Expected {expected_total}, got {total_sum.quantize(Decimal('0.01'))}"
        )
    else:
        print(f"  Total OK: {total_sum.quantize(Decimal('0.01'))}")

    parser_warnings = data.get("warnings", [])
    if parser_warnings:
        warnings.append(f"{output_file}: parser warnings present: {parser_warnings}")


def check_ocr_cache(warnings: list[str]) -> None:
    print("\nChecking OCR cache")

    for output_file in EXPECTED_INVOICES:
        stem = output_file.replace("_labels.json", "")
        ocr_path = OCR_DIR / f"{stem}_ocr.txt"

        if ocr_path.exists():
            print(f"  OK: {ocr_path}")
        else:
            warnings.append(f"Missing OCR cache file: {ocr_path}")


def check_rejected_document(errors: list[str]) -> None:
    print("\nChecking rejected document")

    rejected_files = sorted(OUTPUT_DIR.glob("*_rejected.json"))

    if not rejected_files:
        errors.append("No rejected output file found. Expected at least one *_rejected.json file.")
        return

    found_valid_rejection = False

    for path in rejected_files:
        data = load_json(path)
        print(f"  Found rejected file: {path.name}")

        if data.get("status") == "rejected" and data.get("reason"):
            found_valid_rejection = True

        if data.get("status") != "rejected":
            errors.append(f"{path.name}: status should be rejected")

        if not data.get("reason"):
            errors.append(f"{path.name}: rejected document should include a reason")

        classification = data.get("classification")
        if isinstance(classification, dict):
            if classification.get("is_supported") is not False:
                errors.append(f"{path.name}: classification.is_supported should be false")

    if not found_valid_rejection:
        errors.append("No valid rejected document with status='rejected' and reason found.")


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []

    if not OUTPUT_DIR.exists():
        raise SystemExit(f"Output directory does not exist: {OUTPUT_DIR}")

    check_ocr_cache(warnings)

    print("\nChecking invoice outputs")

    for output_file, expected in EXPECTED_INVOICES.items():
        check_invoice_output(output_file, expected, errors, warnings)

    check_rejected_document(errors)

    print("\nSummary")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("All checks passed.")


if __name__ == "__main__":
    main()