import logging
import time

from datetime import date, timedelta
from pathlib import Path

from src.companies_house import search_companies
from src.database import (
    initialize_database,
    save_companies,
    get_company_count
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

CHECKPOINT_FILE = DATA_DIR / "backfill_checkpoint.txt"


def subtract_months(source_date, months):
    """Subtract calendar months while keeping a valid day."""

    import calendar

    month_index = source_date.month - 1 - months

    year = source_date.year + month_index // 12
    month = month_index % 12 + 1

    day = min(
        source_date.day,
        calendar.monthrange(year, month)[1]
    )

    return date(year, month, day)


def load_checkpoint():
    if not CHECKPOINT_FILE.exists():
        return None

    value = CHECKPOINT_FILE.read_text(
        encoding="utf-8"
    ).strip()

    if not value:
        return None

    return date.fromisoformat(value)


def save_checkpoint(completed_date):
    CHECKPOINT_FILE.write_text(
        completed_date.isoformat(),
        encoding="utf-8"
    )


def run_historical_collection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    initialize_database()

    start_date = subtract_months(date.today(), 24)
    end_date = date.today() - timedelta(days=1)

    checkpoint = load_checkpoint()

    if checkpoint and checkpoint >= end_date:
        logging.info("Historical collection is already complete.")
        logging.info("Database contains %s companies.", get_company_count())
        return

    current_date = start_date

    if checkpoint and checkpoint >= start_date:
        current_date = checkpoint + timedelta(days=1)

    if current_date > end_date:
        logging.info("No historical dates left to process.")
        return

    total_days = (end_date - current_date).days + 1

    logging.info("Starting historical collection.")
    logging.info("From: %s", current_date)
    logging.info("To: %s", end_date)
    logging.info("Days to process: %s", total_days)

    processed_days = 0

    while current_date <= end_date:
        date_string = current_date.isoformat()

        logging.info(
            "Processing %s (%s/%s)",
            date_string,
            processed_days + 1,
            total_days
        )

        companies = search_companies(
            incorporated_from=date_string,
            incorporated_to=date_string
        )

        save_companies(companies)

        # Save progress only after successful retrieval and storage.
        save_checkpoint(current_date)

        processed_days += 1

        logging.info(
            "Completed %s. Found %s Scottish companies.",
            date_string,
            len(companies)
        )

        current_date += timedelta(days=1)

        # Stay comfortably below the API request rate limit.
        time.sleep(0.6)

    logging.info("Historical collection completed.")
    logging.info(
        "Total companies in database: %s",
        get_company_count()
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    run_historical_collection()