from __future__ import annotations

import re
from typing import Optional

from .utils import non_empty_lines, normalize_date, normalize_text


AMOUNT_PATTERN = r"-?\$?\d[\d,]*(?:\.\d+)?"


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


def is_footer_line(line: str) -> bool:
    lower = line.lower()

    footer_markers = [
        "total usd",
        "please update your system",
        "please contact accounts",
        "please make payments",
        "wire/ach payment",
        "ach routing",
        "wire routing",
        "swift",
        "for questions",
        "phone no",
        "fax no",
        "e-mail",
        "web site",
        "accountsreceivable@switch.com",
        "www.switch.com",
    ]

    return any(marker in lower for marker in footer_markers)


def remove_footer_text(text: str) -> str:
    patterns = [
        r"\bTotal\s+USD\b.*$",
        r"\bPlease update your system\b.*$",
        r"\bPlease contact accounts\b.*$",
        r"\bPlease make payments\b.*$",
        r"\bWire/ACH Payment\b.*$",
        r"\bACH Routing\b.*$",
        r"\bWire Routing\b.*$",
        r"\bSWIFT\b.*$",
        r"\bFor questions\b.*$",
        r"\bPhone No\.\b.*$",
        r"\bFax No\.\b.*$",
        r"\bE-Mail\b.*$",
        r"\bWeb Site\b.*$",
        r"\bwww\.switch\.com\b.*$",
    ]

    cleaned = text

    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned


def is_page_header_or_metadata_line(line: str) -> bool:
    """
    Detect repeated page headers and invoice metadata.
    """
    lower = line.lower().strip()

    # Exact standalone header words only.
    exact_metadata_lines = {
        "switch",
        "invoice",
        "page",
        "invoice date due date invoice no.",
        "invoice date due date invoice no",
        "account no. p.o. number services for month of",
        "account no. p.o. number services for month",
        "description quantity rate amount",
    }

    if lower in exact_metadata_lines:
        return True

    # Combined OCR page-header lines.
    if lower.startswith("invoice switch"):
        return True

    if (
        "invoice date" in lower
        and "due date" in lower
        and "invoice no" in lower
    ):
        return True

    if (
        "account no" in lower
        and "p.o. number" in lower
    ):
        return True

    if (
        "description" in lower
        and "quantity" in lower
        and "rate" in lower
        and "amount" in lower
    ):
        return True

    # Header address lines.
    if re.fullmatch(r"p\.?\s*o\.?\s*box\s+\d+", lower):
        return True

    if re.fullmatch(r"dallas,\s*tx\s*\d{5}(?:-\d{4})?", lower):
        return True

    # Page indicators.
    if re.fullmatch(r"\d+\s+of\s+\d+", lower):
        return True

    if re.fullmatch(r"page\s+\d+\s+of\s+\d+", lower):
        return True

    # Invoice metadata values.
    if re.fullmatch(r"\d{5,}", line.strip()):
        return True

    if re.fullmatch(r"PO-[A-Za-z0-9-]+", line.strip(), flags=re.IGNORECASE):
        return True

    if re.fullmatch(r"[A-Z]-\d+", line.strip()):
        return True

    if re.fullmatch(
        r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}/\d{1,2}/\d{2,4}",
        line.strip(),
    ):
        return True

    # Month-only service period.
    if lower in {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    }:
        return True

    # Customer address lines in repeated page header.
    if re.fullmatch(r"\d+ .+", line.strip()) and not re.search(r"\d+\.\d{2}", line):
        return True

    return False


def is_description_continuation(
    line: str,
    previous_description: str | None = None,
) -> bool:
    """
    Detect lines that continue a previous line-item description.
    """
    lower = line.lower().strip()

    if lower.startswith(("to ", "and ")):
        return True

    if re.match(r"^[A-Za-z]+,\s*[A-Z]{2}\s*\d{5}", line.strip()):
        return True

    if previous_description:
        previous = previous_description.lower().strip()
        if previous.endswith(" and"):
            return True

    return False


def starts_new_item_description(line: str) -> bool:
    lower = line.lower().strip()

    return lower.startswith(
        (
            "transport |",
            "carrier taxes",
            "special partnership discount",
            "item discount",
            "installation of cross connect",
        )
    )


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
        Extract vendor address from the invoice header.
        """
        header_text = " ".join(self.lines[:30])

        po_box_match = re.search(
            r"P\.?\s*O\.?\s*Box\s+\d+",
            header_text,
            flags=re.IGNORECASE,
        )

        city_match = re.search(
            r"Dall[ao]s,\s*TX\s*\d{5}(?:-\d{4})?",
            header_text,
            flags=re.IGNORECASE,
        )

        if po_box_match and city_match:
            po_box = po_box_match.group(0)
            city = city_match.group(0).replace("Dalias", "Dallas")
            return f"{po_box}, {city}"

        if po_box_match:
            return po_box_match.group(0)

        return None

    def extract_invoice_date(self) -> Optional[str]:
        metadata = self._extract_invoice_metadata()
        return metadata.get("invoice_date")

    def extract_invoice_number(self) -> Optional[str]:
        metadata = self._extract_invoice_metadata()
        return metadata.get("invoice_number")

    def _extract_invoice_metadata(self) -> dict:
        """
        Extract values from the area
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

        pending_description_lines = []

        full_item_pattern = re.compile(
            rf"^(?P<description>.+?)\s+"
            rf"(?P<quantity>{AMOUNT_PATTERN})\s+"
            rf"(?P<rate>{AMOUNT_PATTERN})\s+"
            rf"(?P<amount>{AMOUNT_PATTERN})$"
        )

        numeric_only_pattern = re.compile(
            rf"^(?P<quantity>{AMOUNT_PATTERN})\s+"
            rf"(?P<rate>{AMOUNT_PATTERN})\s+"
            rf"(?P<amount>{AMOUNT_PATTERN})$"
        )

        for raw_line in section:
            line = raw_line.strip()

            if not line:
                continue

            if is_footer_line(line):
                # if items or pending_description_lines:
                #     break
                continue

            line = remove_footer_text(line)

            if not line:
                continue

            # Skip repeated page headers and invoice metadata.
            if is_page_header_or_metadata_line(line):
                continue

            candidate = " ".join(pending_description_lines + [line]).strip()
            candidate = remove_footer_text(candidate)

            # Case 1: description + quantity + rate + amount on one line.
            full_match = full_item_pattern.match(candidate)

            if full_match:
                item = {
                    "sku": None,
                    "description": remove_footer_text(
                        full_match.group("description").strip()
                    ),
                    "quantity": parse_amount(full_match.group("quantity")),
                    "tax_rate": None,
                    "price": parse_amount(full_match.group("rate")),
                    "total": parse_amount(full_match.group("amount")),
                }

                items.append(item)
                pending_description_lines = []
                continue

            # Case 2: description lines followed by numeric-only row.
            numeric_match = numeric_only_pattern.match(line)

            if numeric_match and pending_description_lines:
                description = " ".join(pending_description_lines).strip()

                item = {
                    "sku": None,
                    "description": remove_footer_text(description),
                    "quantity": parse_amount(numeric_match.group("quantity")),
                    "tax_rate": None,
                    "price": parse_amount(numeric_match.group("rate")),
                    "total": parse_amount(numeric_match.group("amount")),
                }

                items.append(item)
                pending_description_lines = []
                continue

            # Case 3: continuation of the previous item.
            # Only append clear continuation lines, not arbitrary metadata.
            if (
                items
                and not pending_description_lines
                and is_description_continuation(line, items[-1]["description"])
            ):
                items[-1]["description"] = (
                    items[-1]["description"] + " " + line
                ).strip()
                continue

            # Case 4: start of a new item description.
            if starts_new_item_description(line):
                pending_description_lines = [line]
                continue

            # Case 5: continuation of a pending item description.
            if pending_description_lines:
                pending_description_lines.append(line)
                continue

            # Ignore unrelated OCR noise.
            continue

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

        return [
            line.strip()
            for line in self.lines[start_idx:]
            if line.strip()
        ]

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