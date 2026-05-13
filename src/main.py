from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_veryfi_config
from .invoice_parser import InvoiceParser
from .utils import slugify_filename
from .validators import validate_invoice_json
from .veryfi_client import VeryfiOCRClient, save_ocr_artifacts


SUPPORTED_FILE_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
    ".txt",
}


def iter_input_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    files = [
        path for path in sorted(input_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_EXTENSIONS
    ]

    return files


def get_ocr_text(
    file_path: Path,
    ocr_dir: Path,
    client: VeryfiOCRClient | None,
    use_cache: bool,
) -> str:
    """
    Retrieve OCR text for a document.

    Text files are treated as pre-extracted OCR, which allows the parser to be
    tested without calling the API. For image/PDF documents, the function can
    reuse cached OCR output when available; otherwise, it sends the document to
    Veryfi, stores the OCR artifacts, and returns the ocr_text field.
    """
    stem = slugify_filename(file_path.stem)
    cached_txt = ocr_dir / f"{stem}_ocr.txt"
    raw_json = ocr_dir / f"{stem}_veryfi_raw.json"

    if file_path.suffix.lower() == ".txt":
        return file_path.read_text(encoding="utf-8")

    if use_cache and cached_txt.exists():
        return cached_txt.read_text(encoding="utf-8")

    if client is None:
        raise RuntimeError(
            f"No Veryfi client available for {file_path}."
        )

    response = client.process_file(file_path)
    save_ocr_artifacts(response, cached_txt, raw_json)
    return response["ocr_text"]


def process_document(
    file_path: Path,
    output_dir: Path,
    ocr_dir: Path,
    client: VeryfiOCRClient | None,
    use_cache: bool,
) -> Path:
    ocr_text = get_ocr_text(
        file_path=file_path,
        ocr_dir=ocr_dir,
        client=client,
        use_cache=use_cache,
    )

    parser = InvoiceParser(ocr_text)
    result = parser.parse(file_name=file_path.name)

    validation_warnings = validate_invoice_json(result)
    if validation_warnings:
        result.setdefault("warnings", [])
        result["warnings"].extend(validation_warnings)

    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = "rejected" if result.get("status") == "rejected" else "labels"
    output_path = output_dir / f"{slugify_filename(file_path.stem)}_{suffix}.json"

    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Get invoice annotation labels from Veryfi OCR text."
    )

    parser.add_argument("--input",
                        type=Path,
                        default=Path("data/input"),
                        help="Directory containing input documents.",
                        )
    parser.add_argument("--output",
                        type=Path,
                        default=Path("data/output"),
                        help="Directory where output JSON files will be written.",
                        )
    parser.add_argument("--ocr-dir",
                        type=Path,
                        default=Path("data/ocr"),
                        help="Directory where OCR text and raw API responses are cached.",
                        )
    parser.add_argument("--use-cache",
                        action="store_true",
                        help="Use cached OCR text when available.",
                        )
    parser.add_argument("--no-api",
                        action="store_true",
                        help="Do not initialize Veryfi API client. Useful when input files are .txt or OCR is cached.",
                        )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    client = None
    if not args.no_api:
        config = load_veryfi_config()
        client = VeryfiOCRClient(config)

    files = iter_input_files(args.input)

    if not files:
        print(f"No supported files found in {args.input}")
        return

    for file_path in files:
        try:
            output_path = process_document(
                file_path=file_path,
                output_dir=args.output,
                ocr_dir=args.ocr_dir,
                client=client,
                use_cache=args.use_cache,
            )
            print(f"Processed {file_path.name} -> {output_path}")
        except Exception as exc:
            print(f"ERROR processing {file_path.name}: {exc}")


if __name__ == "__main__":
    main()