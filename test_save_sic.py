import json

from src.database import get_connection, save_companies


with get_connection() as connection:
    row = connection.execute("""
        SELECT company_number, raw_json
        FROM companies
        WHERE sic_codes_json != '[]'
        LIMIT 1
    """).fetchone()

if row is None:
    raise RuntimeError("No company with SIC data found.")

company = json.loads(row["raw_json"])

print(f"Testing company: {row['company_number']}")
print(f"Expected SIC codes: {company.get('sic_codes', [])}")

save_companies([company])

with get_connection() as connection:
    updated = connection.execute("""
        SELECT sic_codes_json
        FROM companies
        WHERE company_number = ?
    """, (row["company_number"],)).fetchone()

    sic_rows = connection.execute("""
        SELECT sic_code, sic_division
        FROM company_sic_codes
        WHERE company_number = ?
        ORDER BY sic_code
    """, (row["company_number"],)).fetchall()

print(f"Stored SIC JSON: {updated['sic_codes_json']}")
print("SIC table records:")

for sic_row in sic_rows:
    print(
        f"{sic_row['sic_code']} "
        f"(division {sic_row['sic_division']})"
    )

print("\nTest completed.")