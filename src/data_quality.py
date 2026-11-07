from src.database import get_connection


def get_data_coverage():
    with get_connection() as connection:

        summary = connection.execute("""
            SELECT
                MIN(date_of_creation) AS earliest_date,
                MAX(date_of_creation) AS latest_date,
                COUNT(*) AS total_companies
            FROM companies
            WHERE date_of_creation IS NOT NULL
        """).fetchone()

        monthly_rows = connection.execute("""
            SELECT
                substr(date_of_creation, 1, 7) AS month,
                COUNT(*) AS company_count
            FROM companies
            WHERE date_of_creation IS NOT NULL
            GROUP BY month
            ORDER BY month
        """).fetchall()

    return summary, monthly_rows


if __name__ == "__main__":
    summary, monthly_rows = get_data_coverage()

    print("\n=== HISTORICAL DATA COVERAGE ===")
    print(f"Total companies: {summary['total_companies']}")
    print(f"Earliest registration: {summary['earliest_date']}")
    print(f"Latest registration: {summary['latest_date']}")
    print(f"Available months: {len(monthly_rows)}")

    print("\n=== MONTHLY REGISTRATIONS ===")

    for row in monthly_rows:
        print(f"{row['month']}: {row['company_count']}")