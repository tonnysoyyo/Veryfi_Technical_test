# Veryfi Data Annotation Technical Test

This project is a Python-based document annotation pipeline for the Veryfi Data Annotations Engineer technical test.

It processes invoice PDFs, obtains OCR text using the Veryfi OCR API, and extracts the required fields into structured JSON files. The extraction logic uses only the `ocr_text` field from the Veryfi API response.

## Extracted Fields

For each accepted invoice, the system extracts:

- vendor name
- vendor address
- bill to name
- invoice number
- date
- line items:
  - sku
  - description
  - quantity
  - tax_rate
  - price
  - total

The provided documents follow a Switch invoice format, so this project uses a template-specific parser for that layout.

## Project Structure

```text
.
├── README.md
├── APPROACH.md
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py
│   ├── document_classifier.py
│   ├── invoice_parser.py
│   ├── main.py
│   ├── switch_invoice_parser.py
│   ├── utils.py
│   ├── validators.py
│   └── veryfi_client.py
├── scripts/
│   └── check_outputs.py
├── tests/
└── data/
    ├── input/
    ├── ocr/
    └── output/
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Veryfi Credentials

Create a `.env` file using `.env.example` as reference:

```env
VERYFI_CLIENT_ID=your_client_id
VERYFI_CLIENT_SECRET=your_client_secret
VERYFI_USERNAME=your_username
VERYFI_API_KEY=your_api_key
```

## Input Documents

Place the provided PDFs in:

```text
data/input/
```

Example:

```text
data/input/
├── synth-switch_v5-14.pdf
├── synth-switch_v5-4.pdf
├── synth-switch_v5-68.pdf
├── synth-switch_v5-7.pdf
├── synth-switch_v5-79.pdf
└── unsupported_document.txt
```

The unsupported document is used to test the rejection logic.

## Run the Pipeline

To process documents with Veryfi OCR:

```bash
python -m src.main --input data/input --output data/output --ocr-dir data/ocr --use-cache
```

To run offline using cached OCR:

```bash
python -m src.main --input data/input --output data/output --ocr-dir data/ocr --use-cache --no-api
```

## Outputs

Accepted invoices are saved as:

```text
data/output/<document_name>_labels.json
```

Rejected documents are saved as:

```text
data/output/<document_name>_rejected.json
```

For each PDF, OCR artifacts are saved as:

```text
data/ocr/<document_name>_ocr.txt
data/ocr/<document_name>_veryfi_raw.json
```

The parser uses only `*_ocr.txt`.

## Switch Invoice Field Mapping

The Switch invoices contain this table:

```text
Description | Quantity | Rate | Amount
```

The mapping is:

| Source column | Output field |
|---|---|
| Description | description |
| Quantity | quantity |
| Rate | price |
| Amount | total |

The source documents do not contain SKU or tax-rate columns, so:

```json
"sku": null,
"tax_rate": null
```

Negative prices and totals are allowed because they can represent discounts or credits.

## Run Output Checks

```bash
python scripts/check_outputs.py
```

## Run Tests

```bash
python -m pytest -q
```

## Notes

This is not a universal invoice parser. It is intentionally optimized for the Switch invoice format provided in the technical test.