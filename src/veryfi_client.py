from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from veryfi import Client

from .config import VeryfiConfig


class VeryfiOCRClient:
    """
    Client wrapper responsible for sending documents to Veryfi's OCR API.

    This class isolates all direct interaction with the Veryfi Python SDK.
    The rest of the application should not depend on Veryfi-specific details;
    it only needs the API response, especially the ocr_text field used by
    the annotation pipeline.
    """

    def __init__(self, config: VeryfiConfig):
        self.client = Client(
            client_id=config.client_id,
            client_secret=config.client_secret,
            username=config.username,
            api_key=config.api_key,
        )

    def process_file(self, file_path: str | Path) -> dict[str, Any]:
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Categories are optional. They can help Veryfi classify expenses, but for
        # this test we only need the OCR text.
        response = self.client.process_document(
            file_path=str(file_path),
            categories=[],
        )

        if "ocr_text" not in response:
            raise KeyError(
                "The Veryfi response does not contain 'ocr_text'. "
                "Inspect the raw response to confirm your API account and endpoint."
            )

        return response


def save_ocr_artifacts(response: dict[str, Any], ocr_text_path: Path, raw_json_path: Path) -> None:
    ocr_text_path.parent.mkdir(parents=True, exist_ok=True)
    raw_json_path.parent.mkdir(parents=True, exist_ok=True)

    ocr_text_path.write_text(response.get("ocr_text", ""), encoding="utf-8")
    raw_json_path.write_text(
        json.dumps(response, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
