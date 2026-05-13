# Approach

## Objective

The objective is to build a Python system that extracts structured annotation labels from invoice documents.

The system uses Veryfi only to obtain OCR text. The custom extraction logic uses the `ocr_text` field from the Veryfi API response and ignores the other automatically extracted fields.

## Pipeline

The pipeline is:

```text
Input PDF
→ Veryfi OCR API
→ ocr_text
→ document classifier
→ Switch invoice parser
→ validator
→ JSON output
```

Main steps:

1. Load documents from `data/input`.
2. Use cached OCR text when available.
3. Call Veryfi OCR when cache is missing.
4. Save OCR text in `data/ocr`.
5. Classify whether the document matches the Switch invoice format.
6. Reject unsupported documents.
7. Extract invoice fields and line items.
8. Validate the final JSON.
9. Save output files in `data/output`.

## Why a Template-Specific Parser?

The provided PDFs follow the same Switch invoice layout. Because the technical test asks the system to support documents with the same format and reject other documents, a template-specific parser is appropriate.

The classifier looks for Switch invoice markers such as:

- `switch`
- `invoice date`
- `due date`
- `invoice no`
- `account no`
- `p.o. number`
- `description`
- `quantity`
- `rate`
- `amount`

If the document does not match this structure, it is rejected.

## Code Organization

### `main.py`

Runs the full pipeline. It reads input files, gets OCR text, calls the parser, validates the result, and writes JSON outputs.

### `config.py`

Loads Veryfi credentials from environment variables.

### `veryfi_client.py`

Wraps the Veryfi Python SDK and saves OCR artifacts.

### `document_classifier.py`

Checks whether the OCR text belongs to the expected Switch invoice format.

### `invoice_parser.py`

Routes accepted Switch invoices to the Switch parser and rejects unsupported documents.

### `switch_invoice_parser.py`

Extracts:

- vendor name
- vendor address
- bill-to name
- invoice number
- invoice date
- line items

It also handles multiline descriptions and removes footer/payment text from line-item descriptions.

### `validators.py`

Checks the structure and quality of the extracted JSON.

### `utils.py`

Contains shared helper functions for text normalization, date normalization, and filename cleaning.

## Field Mapping

The Switch invoice table contains:

```text
Description | Quantity | Rate | Amount
```

This is mapped as:

| Source column | JSON field |
|---|---|
| Description | description |
| Quantity | quantity |
| Rate | price |
| Amount | total |

Because the source table does not include SKU or tax-rate columns:

```json
"sku": null,
"tax_rate": null
```

This is intentional.

## Assumptions

- All provided PDFs follow the Switch invoice format.
- The invoice metadata contains `Invoice Date`, `Due Date`, and `Invoice No.` close together.
- The line-item table contains `Description`, `Quantity`, `Rate`, and `Amount`.
- Negative values can appear because discounts or credits may be represented as negative line items.
- Footer/payment information should not be included in line-item descriptions.

## Validation

The validator checks:

- accepted documents have all required fields,
- rejected documents have a rejection reason,
- dates use `YYYY-MM-DD`,
- line items contain all required keys,
- quantity, price, and total are numeric,
- `sku` and `tax_rate` may be `null`,
- negative prices and totals are allowed.

## Tests

Unit tests are included to verify:

- Switch invoice classification,
- unsupported document rejection,
- parser routing,
- header extraction,
- line-item extraction,
- multiline description handling,
- discount lines,
- footer cleanup,
- JSON validation.

Run tests with:

```bash
python -m pytest -q
```

## Limitations

This solution is not designed as a universal invoice parser. It is optimized for the Switch invoice format provided in the technical test. A different invoice layout would require additional parser rules or a new parser class.