
from src.backtesting import load_monthly_data, calculate_metrics

WEIGHTS = [0.2, 0.3, 0.5]


def previous_year_month(month):
    year, month_number = map(int, month.split("-"))
    return f"{year - 1:04d}-{month_number:02d}"


def run_seasonal_backtest():
    monthly_data, date_range = load_monthly_data()

    all_months = sorted(monthly_data.keys())
    complete_months = all_months[1:-1]

    if len(complete_months) < 13:
        raise ValueError(
            "At least 13 complete months are required."
        )

    divisions = sorted({
        division
        for month_data in monthly_data.values()
        for division in month_data
    })

    errors = {
        "weighted": [],
        "naive": [],
        "seasonal": []
    }

    actual_values = []
    monthly_results = []

    # Start after 12 complete months of history.
    for index in range(12, len(complete_months)):
        target_month = complete_months[index]

        previous_months = complete_months[index - 3:index]
        seasonal_month = previous_year_month(target_month)

        month_errors = {
            "weighted": [],
            "naive": [],
            "seasonal": []
        }

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
                    historical_values, WEIGHTS
                )
            )

            naive_forecast = historical_values[-1]

            seasonal_forecast = monthly_data.get(
                seasonal_month, {}
            ).get(division, 0)

            forecasts = {
                "weighted": weighted_forecast,
                "naive": naive_forecast,
                "seasonal": seasonal_forecast
            }

            for model, forecast in forecasts.items():
                error = abs(actual - forecast)
                errors[model].append(error)
                month_errors[model].append(error)

            actual_values.append(actual)

        monthly_results.append({
            "month": target_month,
            "weighted_mae": sum(
                month_errors["weighted"]
            ) / len(month_errors["weighted"]),
            "naive_mae": sum(
                month_errors["naive"]
            ) / len(month_errors["naive"]),
            "seasonal_mae": sum(
                month_errors["seasonal"]
            ) / len(month_errors["seasonal"])
        })

    results = {}

    for model, model_errors in errors.items():
        results[model] = calculate_metrics(
            model_errors,
            actual_values
        )

    return {
        "first_test_month": complete_months[12],
        "last_test_month": complete_months[-1],
        "test_months": len(monthly_results),
        "results": results,
        "monthly_results": monthly_results
    }


if __name__ == "__main__":
    result = run_seasonal_backtest()

    print("=== THREE-MODEL COMPARISON ===")
    print(
        f"Test period: {result['first_test_month']} "
        f"to {result['last_test_month']}"
    )
    print(f"Test months: {result['test_months']}")

    for model, metrics in result["results"].items():
        print(f"\n{model.upper()}:")
        print(f"MAE: {metrics['mae']}")
        print(f"WAPE: {metrics['wape']}%")

    print("\n=== MONTHLY MAE COMPARISON ===")

    for row in result["monthly_results"]:
        print(
            f"{row['month']}: "
            f"Weighted={row['weighted_mae']:.2f}, "
            f"Naive={row['naive_mae']:.2f}, "
            f"Seasonal={row['seasonal_mae']:.2f}"
        )
