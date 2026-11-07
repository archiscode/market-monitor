from datetime import date, timedelta
from statistics import median

from src.database import get_connection


def get_weekly_industry_counts(weeks=9):
    """
    Return weekly registration counts for each SIC division.

    The current incomplete week is excluded.
    """

    today = date.today()

    # Monday of the current week.
    current_week_start = today - timedelta(days=today.weekday())

    # Last fully completed week.
    target_week_start = current_week_start - timedelta(days=7)

    # Include the target week and the previous eight weeks.
    start_date = target_week_start - timedelta(weeks=weeks - 1)
    end_date = target_week_start + timedelta(days=6)

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                date(
                    companies.date_of_creation,
                    '-' || (
                        (
                            CAST(strftime(
                                '%w',
                                companies.date_of_creation
                            ) AS INTEGER) + 6
                        ) % 7
                    ) || ' days'
                ) AS week_start,

                company_sic_codes.sic_division,

                COUNT(DISTINCT companies.company_number)
                    AS company_count

            FROM companies

            JOIN company_sic_codes
                ON companies.company_number =
                   company_sic_codes.company_number

            WHERE companies.date_of_creation >= ?
              AND companies.date_of_creation <= ?

            GROUP BY
                week_start,
                company_sic_codes.sic_division

            ORDER BY
                week_start,
                company_sic_codes.sic_division
        """, (
            start_date.isoformat(),
            end_date.isoformat()
        )).fetchall()

    result = {}

    for row in rows:
        division = row["sic_division"]
        week_start = row["week_start"]

        result.setdefault(division, {})
        result[division][week_start] = row["company_count"]

    return result, target_week_start, start_date


def detect_anomalies(minimum_registrations=10):
    """
    Detect unusually high weekly registrations by SIC division.

    Uses the median and median absolute deviation (MAD)
    from the previous eight completed weeks.
    """

    weekly_data, target_week, baseline_start = (
        get_weekly_industry_counts(weeks=9)
    )

    anomalies = []

    baseline_weeks = [
        baseline_start + timedelta(weeks=index)
        for index in range(8)
    ]

    target_key = target_week.isoformat()

    for division, counts in weekly_data.items():

        historical_counts = [
            counts.get(week.isoformat(), 0)
            for week in baseline_weeks
        ]

        current_count = counts.get(target_key, 0)

        baseline_median = median(historical_counts)

        absolute_deviations = [
            abs(value - baseline_median)
            for value in historical_counts
        ]

        mad = median(absolute_deviations)

        # Robust estimate of the upper threshold.
        threshold = max(
            baseline_median + 5,
            baseline_median * 2,
            baseline_median + (3 * 1.4826 * mad)
        )

        if (
            current_count >= minimum_registrations
            and current_count > threshold
        ):
            if baseline_median > 0:
                growth = (
                    (current_count - baseline_median)
                    / baseline_median
                ) * 100
            else:
                growth = None

            anomalies.append({
                "sic_division": division,
                "week_start": target_key,
                "current_count": current_count,
                "baseline_median": baseline_median,
                "threshold": round(threshold, 2),
                "growth_percent": (
                    round(growth, 1)
                    if growth is not None
                    else None
                )
            })

    anomalies.sort(
        key=lambda item: item["current_count"],
        reverse=True
    )

    return anomalies