from src.sic_codes import get_industry_name

from datetime import date

from src.database import get_connection


WEIGHTS = [0.2, 0.3, 0.5]
WEIGHTED_SHARE = 0.5
SEASONAL_SHARE = 0.5


def get_previous_months(count=3):
    """Return the last completed calendar months."""

    today = date.today()
    current_month = today.replace(day=1)

    months = []

    for _ in range(count):
        if current_month.month == 1:
            previous_month = current_month.replace(
                year=current_month.year - 1,
                month=12
            )
        else:
            previous_month = current_month.replace(
                month=current_month.month - 1
            )

        months.append(previous_month.strftime("%Y-%m"))
        current_month = previous_month

    return list(reversed(months))


def get_next_month():
    """Return the next calendar month."""

    today = date.today()

    if today.month == 12:
        return date(today.year + 1, 1, 1).strftime("%Y-%m")

    return date(today.year, today.month + 1, 1).strftime("%Y-%m")


def get_previous_year_month(month):
    """Return the same calendar month in the previous year."""

    year, month_number = map(int, month.split("-"))

    return f"{year - 1:04d}-{month_number:02d}"



def get_monthly_industry_data():
    """Load monthly company registrations by SIC division."""

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    SUBSTRING(
                        companies.date_of_creation FROM 1 FOR 7
                    ) AS month,
                    company_sic_codes.sic_division,
                    COUNT(DISTINCT companies.company_number)
                        AS company_count

                FROM companies

                JOIN company_sic_codes
                    ON companies.company_number =
                       company_sic_codes.company_number

                WHERE companies.date_of_creation IS NOT NULL

                GROUP BY
                    month,
                    company_sic_codes.sic_division

                ORDER BY month
            """)

            rows = cursor.fetchall()

    return rows


def forecast_industries():
    """
    Forecast registrations by SIC division
    using a hybrid weighted and seasonal model.
    """

    months = get_previous_months(count=3)
    target_month = get_next_month()
    seasonal_month = get_previous_year_month(target_month)

    rows = get_monthly_industry_data()

    industry_data = {}
    available_months = set()

    for row in rows:
        division = row["sic_division"]
        month = row["month"]

        available_months.add(month)

        industry_data.setdefault(division, {})
        industry_data[division][month] = row["company_count"]

    # Use seasonal forecasting only when the historical month exists.
    seasonal_available = seasonal_month in available_months

    forecasts = []

    for division, monthly_counts in industry_data.items():

        historical_values = [
            monthly_counts.get(month, 0)
            for month in months
        ]

        weighted_forecast = sum(
            value * weight
            for value, weight in zip(historical_values, WEIGHTS)
        )

        if seasonal_available:
            seasonal_forecast = monthly_counts.get(
                seasonal_month, 0
            )

            forecast_value = (
                weighted_forecast * WEIGHTED_SHARE
                + seasonal_forecast * SEASONAL_SHARE
            )

            model_used = "hybrid"

        else:
            seasonal_forecast = None
            forecast_value = weighted_forecast
            model_used = "weighted_fallback"

        forecasts.append({
            "industry_name": get_industry_name(division),
            "sic_division": division,
            "forecast": round(forecast_value, 1),
            "weighted_forecast": round(weighted_forecast, 1),
            "seasonal_forecast": (
                round(seasonal_forecast, 1)
                if seasonal_forecast is not None
                else None
            ),
            "historical_values": historical_values,
            "seasonal_month": seasonal_month,
            "model_used": model_used
        })

    forecasts.sort(
        key=lambda item: item["forecast"],
        reverse=True
    )

    return target_month, months, forecasts


if __name__ == "__main__":
    target_month, historical_months, forecasts = forecast_industries()

    print("=== HYBRID INDUSTRY FORECAST ===")
    print(f"Forecast month: {target_month}")
    print(f"Historical months: {', '.join(historical_months)}")

    if forecasts:
        print(f"Seasonal reference: {forecasts[0]['seasonal_month']}")

    print("\nTOP 10 INDUSTRIES:")

    for position, item in enumerate(forecasts[:10], start=1):
        print(
            f"{position}. {item['industry_name']} "
            f"(SIC {item['sic_division']}): "
            f"{item['forecast']} "
            f"(Weighted: {item['weighted_forecast']}, "
            f"Seasonal: {item['seasonal_forecast']}, "
            f"Model: {item['model_used']})"
        )
