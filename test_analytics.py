from datetime import date

from src.analytics import (
    get_top_industries,
    get_weekly_registrations,
    get_total_companies
)


today = date.today()
month_start = today.replace(day=1)

print("\n=== DATABASE SUMMARY ===")
print(f"Total companies: {get_total_companies()}")

print("\n=== TOP 10 INDUSTRIES THIS MONTH ===")

industries = get_top_industries(
    month_start.isoformat(),
    today.isoformat()
)

if industries:
    for index, industry in enumerate(industries, start=1):
        print(
            f"{index}. SIC division "
            f"{industry['sic_division']}: "
            f"{industry['company_count']} companies"
        )
else:
    print("No industry data available for this month.")

print("\n=== WEEKLY REGISTRATIONS ===")

weekly_data = get_weekly_registrations(weeks=12)

if weekly_data:
    for week in weekly_data:
        print(
            f"{week['week_start']}: "
            f"{week['company_count']} companies"
        )
else:
    print("No weekly registration data available.")