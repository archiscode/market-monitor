
from itertools import product

from src.backtesting import load_monthly_data


FIXED_WEIGHTS = (0.2, 0.3, 0.5)
VALIDATION_START = "2025-03"
VALIDATION_END = "2025-11"
TEST_START = "2025-12"
TEST_END = "2026-10"


def get_previous_months(month):
    year, month_number = map(int, month.split("-"))

    result = []

    for offset in (3, 2, 1):
        current_month = month_number - offset
        current_year = year

        while current_month <= 0:
            current_month += 12
            current_year -= 1

        result.append(f"{current_year:04d}-{current_month:02d}")

    return result


def calculate_metrics(errors, actual_values):
    if not errors:
        return {"mae": 0.0, "wape": 0.0}

    absolute_error = sum(abs(error) for error in errors)
    actual_total = sum(actual_values)

    mae = absolute_error / len(errors)
    wape = (
        absolute_error / actual_total * 100
        if actual_total > 0
        else 0.0
    )

    return {
        "mae": round(mae, 2),
        "wape": round(wape, 2),
    }


def evaluate_model(monthly_data, divisions, target_months, model, weights=None):
    errors = []
    actual_values = []

    for target_month in target_months:
        previous_months = get_previous_months(target_month)

        for division in divisions:
            historical_values = [
                monthly_data.get(month, {}).get(division, 0)
                for month in previous_months
            ]

            actual = monthly_data.get(target_month, {}).get(division, 0)

            if model == "naive":
                forecast = historical_values[-1]

            elif model == "simple":
                forecast = sum(historical_values) / 3

            elif model == "weighted":
                forecast = sum(
                    value * weight
                    for value, weight in zip(historical_values, weights)
                )

            elif model == "seasonal":
                year, month_number = map(int, target_month.split("-"))
                previous_year_month = f"{year - 1:04d}-{month_number:02d}"
                forecast = monthly_data.get(
                    previous_year_month, {}
                ).get(division, 0)

            elif model == "hybrid":
                weighted_forecast = sum(
                    value * weight
                    for value, weight in zip(
                        historical_values, FIXED_WEIGHTS
                    )
                )

                year, month_number = map(int, target_month.split("-"))
                previous_year_month = f"{year - 1:04d}-{month_number:02d}"
                seasonal_forecast = monthly_data.get(
                    previous_year_month, {}
                ).get(division, 0)

                forecast = (
                    weighted_forecast * 0.5
                    + seasonal_forecast * 0.5
                )

            else:
                raise ValueError(f"Unknown model: {model}")

            errors.append(actual - forecast)
            actual_values.append(actual)

    return calculate_metrics(errors, actual_values)


def optimise_weights(monthly_data, divisions, validation_months):
    best_weights = None
    best_metrics = None

    # Search weights in 10% increments.
    for values in product(range(11), repeat=3):
        if sum(values) != 10:
            continue

        weights = tuple(value / 10 for value in values)

        metrics = evaluate_model(
            monthly_data,
            divisions,
            validation_months,
            "weighted",
            weights,
        )

        if best_metrics is None or metrics["wape"] < best_metrics["wape"]:
            best_weights = weights
            best_metrics = metrics

    return best_weights, best_metrics


def run_comparison():
    monthly_data, date_range = load_monthly_data()

    divisions = sorted({
        division
        for month_data in monthly_data.values()
        for division in month_data
    })

    validation_months = [
        month
        for month in sorted(monthly_data)
        if VALIDATION_START <= month <= VALIDATION_END
    ]

    test_months = [
        month
        for month in sorted(monthly_data)
        if TEST_START <= month <= TEST_END
    ]

    if len(validation_months) != 9:
        raise ValueError(
            f"Expected 9 validation months, found {len(validation_months)}."
        )

    if len(test_months) != 11:
        raise ValueError(
            f"Expected 11 test months, found {len(test_months)}."
        )

    # Optimise weights using validation data only.
    optimised_weights, validation_metrics = optimise_weights(
        monthly_data,
        divisions,
        validation_months,
    )

    models = {
        "Naive": ("naive", None),
        "Simple Moving Average": ("simple", None),
        "Weighted Moving Average": ("weighted", FIXED_WEIGHTS),
        "Optimised Weighted Moving Average": (
            "weighted",
            optimised_weights,
        ),
        "Hybrid": ("hybrid", None),
        "Seasonal": ("seasonal", None),
    }

    print("=== DATA SPLIT ===")
    print(f"Validation: {validation_months[0]} to {validation_months[-1]}")
    print(f"Final test: {test_months[0]} to {test_months[-1]}")
    print(f"Test months: {len(test_months)}")

    print("\n=== OPTIMISED WEIGHTS ===")
    print(f"Weights: {optimised_weights}")
    print(f"Validation WAPE: {validation_metrics['wape']}%")

    print("\n=== FINAL TEST COMPARISON ===")

    results = {}

    for name, (model, weights) in models.items():
        metrics = evaluate_model(
            monthly_data,
            divisions,
            test_months,
            model,
            weights,
        )

        results[name] = metrics

        print(f"\n{name}:")
        print(f"MAE: {metrics['mae']}")
        print(f"WAPE: {metrics['wape']}%")

    best_model = min(
        results,
        key=lambda name: results[name]["wape"],
    )

    print("\n=== CONCLUSION ===")
    print(f"Best model by WAPE: {best_model}")

    print("\n=== MODEL RANKING ===")

    ranking = sorted(
        results.items(),
        key=lambda item: item[1]["wape"],
    )

    for position, (name, metrics) in enumerate(ranking, start=1):
        print(
            f"{position}. {name}: "
            f"WAPE={metrics['wape']}%, MAE={metrics['mae']}"
        )

    return results


if __name__ == "__main__":
    run_comparison()
