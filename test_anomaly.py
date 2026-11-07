from src.anomaly_detection import detect_anomalies


print("\n=== INDUSTRY ANOMALY DETECTION ===")

anomalies = detect_anomalies()

if not anomalies:
    print("No unusual registration spikes detected.")
else:
    for anomaly in anomalies:
        print(f"\nSIC division: {anomaly['sic_division']}")
        print(f"Week: {anomaly['week_start']}")
        print(f"Registrations: {anomaly['current_count']}")
        print(f"Historical median: {anomaly['baseline_median']}")
        print(f"Anomaly threshold: {anomaly['threshold']}")

        if anomaly["growth_percent"] is not None:
            print(f"Growth: {anomaly['growth_percent']}%")
        else:
            print("Growth: baseline median is zero")