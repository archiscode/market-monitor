import logging

from src.companies_house import get_yesterdays_companies
from src.database import (
    initialize_database,
    save_companies,
    get_company_count
)


def main():
    logging.info("Starting Companies House collector.")

    initialize_database()

    companies = get_yesterdays_companies()

    save_companies(companies)

    total = get_company_count()

    print("\nCollection completed.")
    print(f"Companies retrieved: {len(companies)}")
    print(f"Total companies in database: {total}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()