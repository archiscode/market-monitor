
import os
import logging
import time

from datetime import date, timedelta, datetime
from email.utils import parsedate_to_datetime
from datetime import timezone
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY")

BASE_URL = "https://api.company-information.service.gov.uk"
SEARCH_ENDPOINT = "/advanced-search/companies"

PAGE_SIZE = 5000
MAX_RETRIES = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_retry_delay(response, attempt):
    retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            return max(1, float(retry_after))
        except ValueError:
            try:
                retry_time = parsedate_to_datetime(retry_after)

                if retry_time.tzinfo is None:
                    retry_time = retry_time.replace(tzinfo=timezone.utc)

                delay = (
                    retry_time - datetime.now(timezone.utc)
                ).total_seconds()

                return max(1, delay)
            except (TypeError, ValueError):
                pass

    return min(30 * (2 ** attempt), 300)


def request_page(session, url, params):
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(
                url,
                params=params,
                timeout=30
            )

            if response.status_code == 404:
                return None

            if response.status_code == 429:
                delay = get_retry_delay(response, attempt)

                logging.warning(
                    "Rate limit reached. Waiting %.1f seconds.",
                    delay
                )

                time.sleep(delay)
                continue

            if response.status_code in (500, 502, 503, 504):
                delay = min(2 ** attempt, 30)

                logging.warning(
                    "Server error %s. Retrying in %s seconds.",
                    response.status_code,
                    delay
                )

                time.sleep(delay)
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException:
            if attempt == MAX_RETRIES - 1:
                raise

            delay = min(2 ** attempt, 30)

            logging.warning(
                "Network error. Retrying in %s seconds.",
                delay,
                exc_info=True
            )

            time.sleep(delay)

    raise RuntimeError("Maximum API retry attempts exceeded.")


def search_companies(incorporated_from, incorporated_to):
    """
    Retrieve companies incorporated within a date range.
    Return only companies with Scottish registration numbers.
    """

    if not API_KEY:
        raise ValueError("Companies House API key not found.")

    url = f"{BASE_URL}{SEARCH_ENDPOINT}"

    params = {
        "incorporated_from": incorporated_from,
        "incorporated_to": incorporated_to,
        "size": PAGE_SIZE,
        "start_index": 0
    }

    scottish_companies = []

    with requests.Session() as session:
        session.auth = (API_KEY, "")

        while True:
            response = request_page(
                session,
                url,
                params
            )

            if response is None:
                logging.info("No companies found for this date range.")
                break

            data = response.json()

            items = data.get("items", [])
            total_hits = int(data.get("hits", 0))

            if not items:
                break

            for company in items:
                company_number = company.get("company_number", "")

                if company_number.upper().startswith("SC"):
                    scottish_companies.append(company)

            logging.info(
                "Retrieved %s of approximately %s results.",
                params["start_index"] + len(items),
                total_hits
            )

            params["start_index"] += len(items)

            if params["start_index"] >= total_hits:
                break

    logging.info(
        "Found %s Scottish companies.",
        len(scottish_companies)
    )

    return scottish_companies


def get_yesterdays_companies():
    london_today = datetime.now(
        ZoneInfo("Europe/London")
    ).date()

    yesterday = london_today - timedelta(days=1)
    date_string = yesterday.isoformat()

    logging.info(
        "Collecting companies incorporated on %s.",
        date_string
    )

    return search_companies(
        incorporated_from=date_string,
        incorporated_to=date_string
    )


if __name__ == "__main__":
    companies = get_yesterdays_companies()

    for company in companies:
        print(
            company.get("company_number"),
            company.get("company_name"),
            company.get("date_of_creation")
        )
