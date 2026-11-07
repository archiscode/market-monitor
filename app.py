
from datetime import date, timedelta
from statistics import median

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import get_connection
from src.forecasting import forecast_industries
from src.sic_codes import get_industry_name


st.set_page_config(
    page_title="Scottish Companies Monitor",
    page_icon="📊",
    layout="wide"
)



@st.cache_data(ttl=300)
def load_overview():
    with get_connection() as connection:
        summary_row = connection.execute("""
            SELECT
                COUNT(*) AS total_companies,
                MIN(date_of_creation) AS earliest_date,
                MAX(date_of_creation) AS latest_date
            FROM companies
            WHERE date_of_creation IS NOT NULL
        """).fetchone()

        monthly_rows = connection.execute("""
            SELECT
                SUBSTRING(companies.date_of_creation FROM 1 FOR 7) AS month,
                COUNT(*) AS company_count
            FROM companies
            WHERE date_of_creation IS NOT NULL
            GROUP BY month
            ORDER BY month
        """).fetchall()

    summary = dict(summary_row)
    monthly_data = [dict(row) for row in monthly_rows]

    return summary, monthly_data



@st.cache_data(ttl=300)
def load_industry_data():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                substr(companies.date_of_creation, 1, 7) AS month,
                company_sic_codes.sic_division,
                COUNT(DISTINCT companies.company_number) AS company_count
            FROM companies
            JOIN company_sic_codes
                ON companies.company_number =
                   company_sic_codes.company_number
            WHERE companies.date_of_creation IS NOT NULL
            GROUP BY month, company_sic_codes.sic_division
            ORDER BY month
        """).fetchall()

    return pd.DataFrame(
        [dict(row) for row in rows]
    )


@st.cache_data(ttl=300)
def load_weekly_data():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT date_of_creation
            FROM companies
            WHERE date_of_creation IS NOT NULL
        """).fetchall()

    weekly_counts = {}

    for row in rows:
        registration_date = date.fromisoformat(
            row["date_of_creation"][:10]
        )

        week_start = registration_date - timedelta(
            days=registration_date.weekday()
        )

        weekly_counts[week_start] = (
            weekly_counts.get(week_start, 0) + 1
        )

    return weekly_counts



def get_anomalies(weekly_counts):
    today = date.today()
    current_week = today - timedelta(days=today.weekday())

    completed_weeks = sorted(
        week for week in weekly_counts
        if week < current_week
    )

    if len(completed_weeks) < 9:
        return pd.DataFrame(), None

    baseline_weeks = completed_weeks[-9:-1]
    test_week = completed_weeks[-1]

    baseline_values = [
        weekly_counts[week]
        for week in baseline_weeks
    ]

    actual = weekly_counts[test_week]

    baseline = median(baseline_values)

    deviations = [
        abs(value - baseline)
        for value in baseline_values
    ]

    mad = median(deviations)

    threshold = max(
        baseline + 5,
        baseline * 2,
        baseline + 3 * 1.4826 * mad
    )

    anomalies = []

    if actual > threshold:
        anomalies.append({
            "Week starting": test_week.isoformat(),
            "Registrations": actual,
            "Baseline": round(baseline, 1),
            "Threshold": round(threshold, 1)
        })

    return pd.DataFrame(anomalies), threshold



def main():
    st.title("Scottish Companies Monitor")
    st.caption(
        "Companies House registration analytics for Scottish companies"
    )

    summary, monthly_rows = load_overview()
    industry_df = load_industry_data()

    total = summary["total_companies"]
    earliest = summary["earliest_date"]
    latest = summary["latest_date"]

    col1, col2, col3 = st.columns(3)

    col1.metric("Total companies", f"{total:,}")
    col2.metric("First registration", earliest or "N/A")
    col3.metric("Latest registration", latest or "N/A")

    st.divider()

    overview_tab, industry_tab, forecast_tab, anomaly_tab = st.tabs([
        "Overview",
        "Industry Analysis",
        "Forecast",
        "Anomalies"
    ])

    with overview_tab:
        st.subheader("Monthly registrations")

        monthly_df = pd.DataFrame(
            [dict(row) for row in monthly_rows]
        )

        if not monthly_df.empty:
            monthly_df = monthly_df.tail(12)

            figure = px.line(
                monthly_df,
                x="month",
                y="company_count",
                markers=True,
                title="Company registrations per month"
            )

            figure.update_layout(
                xaxis_title="Month",
                yaxis_title="Registered companies"
            )

            st.plotly_chart(figure, use_container_width=True)

        st.subheader("Database coverage")
        st.write(
            f"Currently storing {total:,} companies "
            f"registered between {earliest} and {latest}."
        )

    with industry_tab:
        st.subheader("Industry registrations")

        if not industry_df.empty:
            available_months = sorted(industry_df["month"].unique())

            last_complete_month = (
                date.today().replace(day=1) - timedelta(days=1)
            ).strftime("%Y-%m")

            if last_complete_month in available_months:
                selected_month = last_complete_month
            else:
                selected_month = available_months[-1]

            month_df = industry_df[
                industry_df["month"] == selected_month
            ].copy()

            month_df["industry"] = month_df["sic_division"].apply(
                get_industry_name
            )

            month_df = month_df.sort_values(
                "company_count",
                ascending=False
            )

            st.caption(f"Showing {selected_month}")

            top_df = month_df.head(10)

            figure = px.bar(
                top_df,
                x="company_count",
                y="industry",
                orientation="h",
                title="Top 10 industries",
                labels={
                    "company_count": "Registrations",
                    "industry": "Industry"
                }
            )

            figure.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            st.plotly_chart(figure, use_container_width=True)

            st.dataframe(
                top_df[
                    ["sic_division", "industry", "company_count"]
                ].rename(columns={
                    "sic_division": "SIC division",
                    "industry": "Industry",
                    "company_count": "Companies"
                }),
                hide_index=True,
                use_container_width=True
            )

    with forecast_tab:
        st.subheader("Industry forecast")

        target_month, historical_months, forecasts = (
            forecast_industries()
        )

        st.metric("Forecast month", target_month)

        st.caption(
            "Historical months: " + ", ".join(historical_months)
        )

        forecast_df = pd.DataFrame(forecasts[:10])

        if not forecast_df.empty:
            forecast_df["industry"] = forecast_df[
                "sic_division"
            ].apply(get_industry_name)

            st.dataframe(
                forecast_df[
                    [
                        "sic_division",
                        "industry",
                        "forecast",
                        "weighted_forecast",
                        "seasonal_forecast",
                        "model_used"
                    ]
                ].rename(columns={
                    "sic_division": "SIC division",
                    "industry": "Industry",
                    "forecast": "Hybrid forecast",
                    "weighted_forecast": "Weighted",
                    "seasonal_forecast": "Seasonal",
                    "model_used": "Model"
                }),
                hide_index=True,
                use_container_width=True
            )

            figure = px.bar(
                forecast_df,
                x="forecast",
                y="industry",
                orientation="h",
                title=f"Top 10 forecast industries: {target_month}"
            )

            figure.update_layout(
                yaxis={"categoryorder": "total ascending"},
                xaxis_title="Forecast registrations",
                yaxis_title="Industry"
            )

            st.plotly_chart(figure, use_container_width=True)

    with anomaly_tab:
        st.subheader("Unusual registration activity")

        weekly_counts = load_weekly_data()
        anomalies_df, threshold = get_anomalies(weekly_counts)

        if threshold is None:
            st.info(
                "At least 9 completed weeks of data are required."
            )
        else:
            st.metric("Anomaly threshold", f"{threshold:.1f}")

            if anomalies_df.empty:
                st.success("No unusual registration spikes detected.")
            else:
                st.warning("Unusual registration spikes detected.")

                st.dataframe(
                    anomalies_df,
                    hide_index=True,
                    use_container_width=True
                )


if __name__ == "__main__":
    main()
