from src.forecasting import forecast_industries


target_month, historical_months, forecasts = forecast_industries()

print("\n=== INDUSTRY FORECAST ===")
print(f"Forecast month: {target_month}")

print("\nHistorical months:")
for month in historical_months:
    print(f"- {month}")

print("\n=== TOP 10 FORECASTED INDUSTRIES ===")

if not forecasts:
    print("No industry data available.")
else:
    for index, item in enumerate(forecasts[:10], start=1):
        print(
            f"{index}. SIC division {item['sic_division']}: "
            f"{item['forecast']} companies"
        )

        print(
            f"   Historical values: "
            f"{item['historical_values']}"
        )