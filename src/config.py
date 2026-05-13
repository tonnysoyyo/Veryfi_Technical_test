from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass(frozen=True)
class VeryfiConfig:
    client_id: str
    client_secret: str
    username: str
    api_key: str


def load_veryfi_config() -> VeryfiConfig:
    """
    Load Veryfi credentials.

    Required variables:
    - VERYFI_CLIENT_ID
    - VERYFI_CLIENT_SECRET
    - VERYFI_USERNAME
    - VERYFI_API_KEY
    """
    load_dotenv()

    required = {
        "VERYFI_CLIENT_ID": os.getenv("VERYFI_CLIENT_ID"),
        "VERYFI_CLIENT_SECRET": os.getenv("VERYFI_CLIENT_SECRET"),
        "VERYFI_USERNAME": os.getenv("VERYFI_USERNAME"),
        "VERYFI_API_KEY": os.getenv("VERYFI_API_KEY"),
    }

    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing Veryfi credentials: "
            + ", ".join(missing)
        )

    return VeryfiConfig(
        client_id=required["VERYFI_CLIENT_ID"],
        client_secret=required["VERYFI_CLIENT_SECRET"],
        username=required["VERYFI_USERNAME"],
        api_key=required["VERYFI_API_KEY"],
    )