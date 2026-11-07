from collections import defaultdict

from src.database import get_connection


WEIGHTS = [0.2, 0.3, 0.5]


def load_monthly_data():
    """Load monthly registrations by SIC division."""

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                substr(companies.date_of_creation, 1, 7) AS month,
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
        """).fetchall()

        date_range = connection.execute("""
            SELECT
                MIN(date_of_creation) AS earliest_date,
                MAX(date_of_creation) AS latest_date
            FROM companies
            WHERE date_of_creation IS NOT NULL
        """).fetchone()

    monthly_data = defaultdict(dict)

    for row in rows:
        monthly_data[row["month"]][row["sic_division"]] = (
            row["company_count"]
        )

    return monthly_data, date_range


def calculate_metrics(errors, actual_values):
    """Calculate MAE and WAPE."""

    if not errors:
        return {
            "mae": 0,
            "wape": 0
        }

    absolute_error = sum(abs(error) for error in errors)
    actual_total = sum(actual_values)

    mae = absolute_error / len(errors)

    wape = (
        absolute_error / actual_total * 100
        if actual_total > 0
        else 0
    )

    return {
        "mae": round(mae, 2),
        "wape": round(wape, 2)
    }


def run_backtest():
    """Compare weighted and naive forecasts on historical months."""

    monthly_data, date_range = load_monthly_data()

    all_months = sorted(monthly_data.keys())

    # Exclude the first and last months because their data
    # may be incomplete.
    complete_months = all_months[1:-1]

    if len(complete_months) < 4:
        raise ValueError(
            "At least four complete months are required."
        )

    divisions = sorted({
        division
        for month_data in monthly_data.values()
        for division in month_data
    })

    weighted_errors = []
    naive_errors = []
    actual_values = []

    results_by_month = []

    # Each target month uses only its three preceding months.
    for index in range(3, len(complete_months)):

        target_month = complete_months[index]

        previous_months = complete_months[index - 3:index]

        month_errors_weighted = []
        month_errors_naive = []
        month_actuals = []

        for division in divisions:

            historical_values = [
                monthly_data[month].get(division, 0)
                for month in previous_months
            ]

            actual = monthly_data[target_month].get(
                division, 0
            )

            weighted_forecast = sum(
                value * weight
                for value, weight in zip(
                    historical_values,
                    WEIGHTS
                )
            )

            naive_forecast = historical_values[-1]

            weighted_error = abs(
                actual - weighted_forecast
            )

            naive_error = abs(
                actual - naive_forecast
            )

            weighted_errors.append(weighted_error)
            naive_errors.append(naive_error)
            actual_values.append(actual)

            month_errors_weighted.append(weighted_error)
            month_errors_naive.append(naive_error)
            month_actuals.append(actual)

        results_by_month.append({
            "month": target_month,
            "weighted_mae": round(
                sum(month_errors_weighted)
                / len(month_errors_weighted),
                2
            ),
            "naive_mae": round(
                sum(month_errors_naive)
                / len(month_errors_naive),
                2
            )
        })

    weighted_metrics = calculate_metrics(
        weighted_errors,
        actual_values
    )

    naive_metrics = calculate_metrics(
        naive_errors,
        actual_values
    )

    return {
        "first_date": date_range["earliest_date"],
        "last_date": date_range["latest_date"],
        "training_months": complete_months[:3],
        "first_test_month": results_by_month[0]["month"],
        "last_test_month": results_by_month[-1]["month"],
        "test_months": len(results_by_month),
        "weighted": weighted_metrics,
        "naive": naive_metrics,
        "monthly_results": results_by_month
    }