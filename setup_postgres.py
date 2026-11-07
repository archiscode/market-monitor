
import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def initialize_postgres():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in .env")

    with psycopg.connect(DATABASE_URL) as connection:
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

            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN (
                    'companies',
                    'company_sic_codes'
                )
                ORDER BY table_name
            """)

            tables = cursor.fetchall()

    print("PostgreSQL schema initialized.")

    for table in tables:
        print(f"Table created: {table[0]}")


if __name__ == "__main__":
    initialize_postgres()
