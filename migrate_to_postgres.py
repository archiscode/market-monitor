
import os
import sqlite3

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
SQLITE_PATH = PROJECT_ROOT / "data" / "companies.db"

DATABASE_URL = os.getenv("DATABASE_URL")

BATCH_SIZE = 1000


def parse_datetime(value):
    if not value:
        return None

    parsed = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def migrate_companies(sqlite_connection, postgres_cursor):
    sqlite_cursor = sqlite_connection.execute("""
        SELECT
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
        FROM companies
        ORDER BY company_number
    """)

    total = 0

    while True:
        rows = sqlite_cursor.fetchmany(BATCH_SIZE)

        if not rows:
            break

        records = []

        for row in rows:
            records.append((
                row["company_number"],
                row["company_name"],
                row["date_of_creation"],
                row["company_status"],
                row["company_type"],
                row["registered_office_address"],
                parse_datetime(row["first_seen_at"]),
                parse_datetime(row["last_seen_at"]),
                row["raw_json"],
                row["sic_codes_json"]
            ))

        postgres_cursor.executemany("""
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
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (company_number)
            DO UPDATE SET
                company_name = EXCLUDED.company_name,
                date_of_creation = EXCLUDED.date_of_creation,
                company_status = EXCLUDED.company_status,
                company_type = EXCLUDED.company_type,
                registered_office_address =
                    EXCLUDED.registered_office_address,
                first_seen_at = LEAST(
                    companies.first_seen_at,
                    EXCLUDED.first_seen_at
                ),
                last_seen_at = GREATEST(
                    companies.last_seen_at,
                    EXCLUDED.last_seen_at
                ),
                raw_json = EXCLUDED.raw_json,
                sic_codes_json = EXCLUDED.sic_codes_json
        """, records)

        total += len(records)

        print(f"Companies processed: {total:,}")

    return total


def migrate_sic_codes(sqlite_connection, postgres_cursor):
    sqlite_cursor = sqlite_connection.execute("""
        SELECT
            company_number,
            sic_code,
            sic_division
        FROM company_sic_codes
        ORDER BY company_number, sic_code
    """)

    total = 0

    while True:
        rows = sqlite_cursor.fetchmany(BATCH_SIZE)

        if not rows:
            break

        records = [
            (
                row["company_number"],
                row["sic_code"],
                row["sic_division"]
            )
            for row in rows
        ]

        postgres_cursor.executemany("""
            INSERT INTO company_sic_codes (
                company_number,
                sic_code,
                sic_division
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (company_number, sic_code)
            DO UPDATE SET
                sic_division = EXCLUDED.sic_division
        """, records)

        total += len(records)

        print(f"SIC records processed: {total:,}")

    return total


def main():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in .env")

    if not SQLITE_PATH.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {SQLITE_PATH}"
        )

    with closing(sqlite3.connect(SQLITE_PATH)) as sqlite_connection:
        sqlite_connection.row_factory = sqlite3.Row

        source_companies = sqlite_connection.execute(
            "SELECT COUNT(*) FROM companies"
        ).fetchone()[0]

        source_sic_codes = sqlite_connection.execute(
            "SELECT COUNT(*) FROM company_sic_codes"
        ).fetchone()[0]

        print("Starting migration.")
        print(f"SQLite companies: {source_companies:,}")
        print(f"SQLite SIC records: {source_sic_codes:,}")

        with psycopg.connect(DATABASE_URL) as postgres_connection:
            with postgres_connection.cursor() as postgres_cursor:

                migrated_companies = migrate_companies(
                    sqlite_connection,
                    postgres_cursor
                )

                migrated_sic_codes = migrate_sic_codes(
                    sqlite_connection,
                    postgres_cursor
                )

                postgres_cursor.execute("""
                    SELECT COUNT(*) FROM companies
                """)
                target_companies = postgres_cursor.fetchone()[0]

                postgres_cursor.execute("""
                    SELECT COUNT(*) FROM company_sic_codes
                """)
                target_sic_codes = postgres_cursor.fetchone()[0]

        print("\n=== MIGRATION RESULTS ===")
        print(f"Companies processed: {migrated_companies:,}")
        print(f"SIC records processed: {migrated_sic_codes:,}")
        print(f"PostgreSQL companies: {target_companies:,}")
        print(f"PostgreSQL SIC records: {target_sic_codes:,}")

        if (
            target_companies == source_companies
            and target_sic_codes == source_sic_codes
        ):
            print("\nSUCCESS: Migration counts match.")
        else:
            print("\nWARNING: Source and destination counts differ.")


if __name__ == "__main__":
    main()
