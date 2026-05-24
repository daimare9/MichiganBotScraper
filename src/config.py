import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_KEYWORDS_PATH = Path(__file__).parent.parent / "config" / "keywords.yaml"


def load_config() -> dict[str, Any]:
    """Load all runtime configuration from env vars and keywords.yaml."""
    with open(_KEYWORDS_PATH) as fh:
        kw_data = yaml.safe_load(fh)

    keywords: list[str] = kw_data.get("keywords", ["concrete"])

    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient_email = os.environ.get("RECIPIENT_EMAIL", "")

    missing = [
        name
        for name, val in [
            ("GMAIL_USER", gmail_user),
            ("GMAIL_APP_PASSWORD", gmail_app_password),
            ("RECIPIENT_EMAIL", recipient_email),
        ]
        if not val
    ]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your credentials."
        )

    return {
        "keywords": keywords,
        "poll_interval_minutes": int(os.environ.get("POLL_INTERVAL_MINUTES", "20")),
        "gmail_user": gmail_user,
        "gmail_app_password": gmail_app_password,
        "recipient_email": recipient_email,
        "db_path": os.environ.get("DB_PATH", "data/contracts.db"),
    }
