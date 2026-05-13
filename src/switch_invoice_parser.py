from __future__ import annotations

import re
from typing import Optional

from .utils import non_empty_lines, normalize_date, normalize_text


AMOUNT_PATTERN = r"-?\$?\d[\d,]*(?:\.\d{2})"


def parse_amount(value: str | None) -> Optional[float]:
    if value is None:
        return None

    raw = value.strip()
    if not raw:
        return None

    is_negative = raw.startswith("-") or ("(" in raw and ")" in raw)
    cleaned = re.sub(r"[^0-9.]", "", raw)

    if not cleaned:
        return None

    number = float(cleaned)
    return -number if is_negative else number


class SwitchInvoiceParser:
    def __init__(self, ocr_text: str):
        self.text = normalize_text(ocr_text)
        self.lines = non_empty_lines(ocr_text)

    def parse(self, file_name: str | None = None) -> dict:
        result = {
            "status": "accepted",
            "document_type": "switch_invoice",
            "file_name": file_name,
            "vendor_name": self.extract_vendor_name(),
            "vendor_address": self.extract_vendor_address(),
            "bill_to_name": self.extract_bill_to_name(),
            "invoice_number": self.extract_invoice_number(),
            "date": self.extract_invoice_date(),
            "line_items": self.extract_line_items(),
            "warnings": [],
        }

        self.add_warnings(result)
        return result

    def extract_vendor_name(self) -> Optional[str]:
        for line in self.lines[:8]:
            if "switch" in line.lower():
                return "Switch"
        return None

    def extract_vendor_address(self) -> Optional[str]:
        """
        Extract vendor address from the top-left invoice header.

        Expected visual format:
        PO Box 674592
        Dallas, TX 75267-4592
        """
        header_text = " ".join(self.lines[:15])

        match = re.search(
            r"(PO\s+Box\s+\d+)\s+(Dallas,\s*TX\s*\d{5}(?:-\d{4})?)",
            header_text,
            flags=re.IGNORECASE,
        )

        if match:
            return f"{match.group(1)}, {match.group(2)}"

        for i, line in enumerate(self.lines):
            if "po box" in line.lower():
                po_box = line.strip()

                nearby_text = " ".join(self.lines[i:i + 4])
                city_match = re.search(
                    r"Dallas,\s*TX\s*\d{5}(?:-\d{4})?",
                    nearby_text,
                    flags=re.IGNORECASE,
                )

                if city_match:
                    return f"{po_box}, {city_match.group(0)}"

                return po_box

        return None

    def extract_invoice_date(self) -> Optional[str]:
        metadata = self._extract_invoice_metadata()
        return metadata.get("invoice_date")

    def extract_invoice_number(self) -> Optional[str]:
        metadata = self._extract_invoice_metadata()
        return metadata.get("invoice_number")

    def _extract_invoice_metadata(self) -> dict:
        """
        Extract values from the area:

        Invoice Date | Due Date | Invoice No.
        09/22/23       08/27/24   1556267
        """
        metadata = {
            "invoice_date": None,
            "due_date": None,
            "invoice_number": None,
        }

        for i, line in enumerate(self.lines):
            lower = line.lower()

            if "invoice date" in lower and "due date" in lower and "invoice" in lower:
                nearby_text = " ".join(self.lines[i:i + 4])

                dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", nearby_text)
                invoice_numbers = re.findall(r"\b\d{5,}\b", nearby_text)

                if dates:
                    metadata["invoice_date"] = normalize_date(dates[0])

                if len(dates) > 1:
                    metadata["due_date"] = normalize_date(dates[1])

                if invoice_numbers:
                    metadata["invoice_number"] = invoice_numbers[-1]

                return metadata

        return metadata

    def extract_bill_to_name(self) -> Optional[str]:
        """
        The Switch invoice does not show a clear 'Bill To:' label in the screenshot.
        The customer block appears between the invoice metadata and Account No. table.
        """
        account_idx = None

        for i, line in enumerate(self.lines):
            if "account no" in line.lower():
                account_idx = i
                break

        if account_idx is None:
            return None

        candidate_lines = []

        for line in self.lines[:account_idx]:
            lower = line.lower()

            if any(
                marker in lower
                for marker in [
                    "switch",
                    "po box",
                    "dallas",
                    "invoice",
                    "page",
                    "invoice date",
                    "due date",
                ]
            ):
                continue

            if re.fullmatch(r"[\d/ ]+", line.strip()):
                continue

            if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", line):
                continue

            if re.search(r"\b\d{5,}\b", line):
                continue

            candidate_lines.append(line.strip())

        if not candidate_lines:
            return None

        return candidate_lines[-3] if len(candidate_lines) >= 3 else candidate_lines[0]

    def extract_line_items(self) -> list[dict]:
        section = self._extract_line_item_section()
        items = []

        pending_prefix_lines = []

        line_pattern = re.compile(
            rf"^(?P<description>.+?)\s+"
            rf"(?P<quantity>{AMOUNT_PATTERN})\s+"
            rf"(?P<rate>{AMOUNT_PATTERN})\s+"
            rf"(?P<amount>{AMOUNT_PATTERN})$"
        )

        for line in section:
            line = line.strip()
            if not line:
                continue

            candidate = " ".join(pending_prefix_lines + [line]).strip()
            match = line_pattern.match(candidate)

            if match:
                item = {
                    "sku": None,
                    "description": match.group("description").strip(),
                    "quantity": parse_amount(match.group("quantity")),
                    "tax_rate": None,
                    "price": parse_amount(match.group("rate")),
                    "total": parse_amount(match.group("amount")),
                }
                items.append(item)
                pending_prefix_lines = []
                continue

            # If we already have an item and the current line does not contain
            # numeric columns, it is most likely a continuation of the previous
            # description, not the beginning of the next item.
            if items:
                items[-1]["description"] = (
                    items[-1]["description"] + " " + line
                ).strip()
            else:
                pending_prefix_lines.append(line)

        return items

    def _extract_line_item_section(self) -> list[str]:
        start_idx = None

        for i, line in enumerate(self.lines):
            lower = line.lower()

            if (
                "description" in lower
                and "quantity" in lower
                and "rate" in lower
                and "amount" in lower
            ):
                start_idx = i + 1
                break

        if start_idx is None:
            return []

        stop_markers = [
            "subtotal",
            "sub total",
            "total due",
            "amount due",
            "balance due",
            "invoice total",
            "terms",
            "thank you",
        ]

        section = []

        for line in self.lines[start_idx:]:
            lower = line.lower()

            if any(marker in lower for marker in stop_markers):
                break

            if line.strip():
                section.append(line.strip())

        return section

    @staticmethod
    def add_warnings(result: dict) -> None:
        for field in [
            "vendor_name",
            "vendor_address",
            "bill_to_name",
            "invoice_number",
            "date",
        ]:
            if not result.get(field):
                result["warnings"].append(f"Missing or uncertain field: {field}")

        if not result.get("line_items"):
            result["warnings"].append("No line items were extracted.")