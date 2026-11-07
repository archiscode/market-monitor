import json

from src.database import get_connection


with get_connection() as connection:

    print("\n=== DATABASE DIAGNOSTICS ===")

    total = connection.execute("""
        SELECT COUNT(*) FROM companies
    """).fetchone()[0]

    sic_json_count = connection.execute("""
        SELECT COUNT(*)
        FROM companies
        WHERE sic_codes_json IS NOT NULL
          AND sic_codes_json != '[]'
    """).fetchone()[0]

    sic_table_count = connection.execute("""
        SELECT COUNT(*) FROM company_sic_codes
    """).fetchone()[0]

    latest_date = connection.execute("""
        SELECT MAX(date_of_creation)
        FROM companies
    """).fetchone()[0]

    print(f"Total companies: {total}")
    print(f"Companies with SIC JSON: {sic_json_count}")
    print(f"Rows in company_sic_codes: {sic_table_count}")
    print(f"Latest incorporation date: {latest_date}")

    print("\n=== RECENT COMPANIES ===")

    rows = connection.execute("""
        SELECT
            company_number,
            company_name,
            date_of_creation,
            sic_codes_json,
            raw_json
        FROM companies
        ORDER BY date_of_creation DESC
        LIMIT 10
    """).fetchall()

    for row in rows:
        print(f"\n{row['company_number']} - {row['company_name']}")
        print(f"Date: {row['date_of_creation']}")
        print(f"Stored SIC: {row['sic_codes_json']}")

        try:
            raw_data = json.loads(row["raw_json"])
            print(f"Original API SIC: {raw_data.get('sic_codes')}")
        except (TypeError, json.JSONDecodeError):
            print("Could not parse original API response.")