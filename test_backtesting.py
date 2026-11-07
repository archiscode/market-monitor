from src.backtesting import run_backtest


results = run_backtest()

print("\n=== FORECAST BACKTESTING ===")

print(f"Database start: {results['first_date']}")
print(f"Database end: {results['last_date']}")

print("\nTraining months:")
for month in results["training_months"]:
    print(f"- {month}")

print(f"\nFirst test month: {results['first_test_month']}")
print(f"Last test month: {results['last_test_month']}")
print(f"Total test months: {results['test_months']}")

print("\n=== MODEL COMPARISON ===")

print("\nWeighted Moving Average:")
print(f"MAE: {results['weighted']['mae']}")
print(f"WAPE: {results['weighted']['wape']}%")

print("\nNaive Forecast:")
print(f"MAE: {results['naive']['mae']}")
print(f"WAPE: {results['naive']['wape']}%")

weighted_wape = results["weighted"]["wape"]
naive_wape = results["naive"]["wape"]

print("\n=== CONCLUSION ===")

if weighted_wape < naive_wape:
    print("Weighted Moving Average performed better.")
elif weighted_wape > naive_wape:
    print("Naive Forecast performed better.")
else:
    print("Both models performed equally.")

print("\n=== MONTHLY MAE COMPARISON ===")

for month in results["monthly_results"]:
    print(
        f"{month['month']}: "
        f"Weighted MAE = {month['weighted_mae']}, "
        f"Naive MAE = {month['naive_mae']}"
    )