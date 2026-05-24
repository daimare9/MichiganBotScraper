"""
Entry point for Michigan Bot Scraper.

Run directly:  python -m src.main
In Docker:     CMD ["python", "-m", "src.main"]
"""

import logging
import time

import schedule

from .config import load_config
from .database import ContractDatabase
from .email_sender import send_alert
from .models import Contract
from .scrapers.mdot_letting import MDOTLettingScraper
from .scrapers.sigma_vss import SigmaVSSScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_scrape_cycle(config: dict, db: ContractDatabase) -> None:
    logger.info("━" * 60)
    logger.info("Scrape cycle starting…")

    scrapers = [
        MDOTLettingScraper(config["keywords"]),
        SigmaVSSScraper(config["keywords"]),
    ]

    new_contracts: list[Contract] = []

    for scraper in scrapers:
        name = scraper.__class__.__name__
        try:
            found = scraper.scrape()
            fresh = [c for c in found if db.is_new(c)]
            logger.info("%s: %d found, %d new", name, len(found), len(fresh))
            for c in fresh:
                db.mark_seen(c)
                new_contracts.append(c)
        except Exception as exc:
            logger.error("%s raised an unhandled exception: %s", name, exc, exc_info=True)

    if new_contracts:
        logger.info("Sending email alert for %d new contract(s)…", len(new_contracts))
        try:
            send_alert(new_contracts, config)
        except Exception as exc:
            logger.error("Email delivery failed: %s", exc, exc_info=True)
    else:
        logger.info("No new contracts this cycle (total tracked: %d)", db.total_seen())

    logger.info("Scrape cycle complete.")


def main() -> None:
    config = load_config()
    db = ContractDatabase(config["db_path"])

    interval = config["poll_interval_minutes"]
    logger.info("Michigan Bot Scraper started")
    logger.info("Poll interval : every %d minutes", interval)
    logger.info("Keywords      : %s", ", ".join(config["keywords"]))
    logger.info("Recipient     : %s", config["recipient_email"])
    logger.info("Database      : %s", config["db_path"])

    # Run immediately on startup so we don't wait a full interval on first boot
    run_scrape_cycle(config, db)

    # Schedule recurring runs
    schedule.every(interval).minutes.do(run_scrape_cycle, config=config, db=db)

    while True:
        schedule.run_pending()
        time.sleep(30)  # check every 30 s — lightweight busy-wait


if __name__ == "__main__":
    main()
