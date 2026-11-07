
import json
import os

from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    try:
        import streamlit as st
        database_url = st.secrets["DATABASE_URL"]
    except Exception as exc:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Set it in the environment or Streamlit secrets."
        ) from exc

    return database_url


def get_connection():
    return psycopg.connect(
        get_database_url(),
        row_factory=dict_row
    )


def initialize_database():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    company_number TEXT PRIMARY KEY,
                    company_name TEXT,
                    date_of_creation TEXT,
                    company_status TEXT,
                    company_type TEXT,
                    registered_office_address TEXT,
                    first_seen_at TIMESTAMPTZ NOT NULL,
                    last_seen_at TIMESTAMPTZ NOT NULL,
                    raw_json TEXT,
                    sic_codes_json TEXT NOT NULL DEFAULT '[]'
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_companies_date_of_creation
                ON companies(date_of_creation)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_sic_codes (
                    company_number TEXT NOT NULL,
                    sic_code TEXT NOT NULL,
                    sic_division TEXT NOT NULL,
                    PRIMARY KEY (company_number, sic_code),
                    FOREIGN KEY (company_number)
                        REFERENCES companies(company_number)
                        ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_sic_division
                ON company_sic_codes(sic_division)
            """)

    print("PostgreSQL database initialized.")


def save_companies(companies):
    if not companies:
        print("No companies to save.")
        return 0

    current_time = datetime.now(timezone.utc)

    records = []
    sic_records = []
    company_numbers = []

    for company in companies:
        company_number = company.get("company_number")

        if not company_number:
            continue

        address = company.get("registered_office_address") or {}
        sic_codes = company.get("sic_codes") or []

        sic_codes = sorted({
            str(code)
            for code in sic_codes
            if str(code).isdigit() and len(str(code)) == 5
        })

        records.append((
            company_number,
            company.get("company_name"),
            company.get("date_of_creation"),
            company.get("company_status"),
            company.get("company_type"),
            json.dumps(address),
            current_time,
            current_time,
            json.dumps(company),
            json.dumps(sic_codes)
        ))

        company_numbers.append((company_number,))

        for sic_code in sic_codes:
            sic_records.append((
                company_number,
                sic_code,
                sic_code[:2]
            ))

    if not records:
        print("No valid company records found.")
        return 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO companies (
                    company_number,
                    company_name,
                    date_of_creation,
                    company_status,
                    company_type,
                    registered_office_address,
                    first_seen_at,
                    last_seen_at,
                    raw_json,
                    sic_codes_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

                ON CONFLICT (company_number) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    date_of_creation = EXCLUDED.date_of_creation,
                    company_status = EXCLUDED.company_status,
                    company_type = EXCLUDED.company_type,
                    registered_office_address =
                        EXCLUDED.registered_office_address,
                    last_seen_at = EXCLUDED.last_seen_at,
                    raw_json = EXCLUDED.raw_json,
                    sic_codes_json = EXCLUDED.sic_codes_json
            """, records)

            cursor.executemany("""
                DELETE FROM company_sic_codes
                WHERE company_number = %s
            """, company_numbers)

            if sic_records:
                cursor.executemany("""
                    INSERT INTO company_sic_codes (
                        company_number,
                        sic_code,
                        sic_division
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT (company_number, sic_code)
                    DO UPDATE SET
                        sic_division = EXCLUDED.sic_division
                """, sic_records)

    print(f"Processed {len(records)} company records.")
    print(f"Stored {len(sic_records)} SIC codes.")

    return len(records)


def get_company_count():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM companies
            """)

            result = cursor.fetchone()

    return result["total"]
