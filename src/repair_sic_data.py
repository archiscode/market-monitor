import json

from src.database import get_connection


def extract_sic_codes(raw_json):
    """Extract valid five-digit SIC codes from stored API data."""

    try:
        company_data = json.loads(raw_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return []

    sic_codes = company_data.get("sic_codes") or []

    return sorted({
        str(code)
        for code in sic_codes
        if str(code).isdigit() and len(str(code)) == 5
    })


def repair_sic_data():
    with get_connection() as connection:

        companies = connection.execute("""
            SELECT company_number, raw_json
            FROM companies
        """).fetchall()

        company_updates = []
        sic_records = []

        for company in companies:
            company_number = company["company_number"]

            sic_codes = extract_sic_codes(company["raw_json"])

            company_updates.append((
                json.dumps(sic_codes),
                company_number
            ))

            for sic_code in sic_codes:
                sic_records.append((
                    company_number,
                    sic_code,
                    sic_code[:2]
                ))

        # Replace the existing SIC index with recovered data.
        connection.execute("""
            DELETE FROM company_sic_codes
        """)

        connection.executemany("""
            UPDATE companies
            SET sic_codes_json = ?
            WHERE company_number = ?
        """, company_updates)

        if sic_records:
            connection.executemany("""
                INSERT INTO company_sic_codes (
                    company_number,
                    sic_code,
                    sic_division
                )
                VALUES (?, ?, ?)
            """, sic_records)

    print(f"Companies checked: {len(company_updates)}")
    print(f"Companies with SIC codes: {sum(1 for item in company_updates if item[0] != '[]')}")
    print(f"SIC records restored: {len(sic_records)}")


if __name__ == "__main__":
    repair_sic_data()