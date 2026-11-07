import sqlite3
from datetime import date, timedelta

from src.database import get_connection


def get_top_industries(start_date, end_date, limit=10):
    """
    Return the most common SIC divisions for companies
    incorporated within the specified date range.
    """

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                sic_division,
                COUNT(DISTINCT company_sic_codes.company_number)
                    AS company_count
            FROM company_sic_codes
            JOIN companies
                ON companies.company_number =
                   company_sic_codes.company_number
            WHERE companies.date_of_creation >= ?
              AND companies.date_of_creation <= ?
              AND sic_division != '99'
            GROUP BY sic_division
            ORDER BY company_count DESC
            LIMIT ?
        """, (start_date, end_date, limit)).fetchall()

    return [
        {
            "sic_division": row["sic_division"],
            "company_count": row["company_count"]
        }
        for row in rows
    ]


def get_weekly_registrations(weeks=12):
    """
    Return weekly company registration counts
    for the requested number of recent weeks.
    """

    end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                date(
                    date_of_creation,
                    '-' || (
                        (CAST(strftime('%w', date_of_creation) AS INTEGER) + 6)
                        % 7
                    ) || ' days'
                ) AS week_start,
                COUNT(*) AS company_count
            FROM companies
            WHERE date_of_creation >= ?
              AND date_of_creation <= ?
            GROUP BY week_start
            ORDER BY week_start
        """, (start_date.isoformat(), end_date.isoformat())).fetchall()

    return [
        {
            "week_start": row["week_start"],
            "company_count": row["company_count"]
        }
        for row in rows
    ]


def get_total_companies():
    """Return the total number of stored companies."""

    with get_connection() as connection:
        row = connection.execute("""
            SELECT COUNT(*) AS total
            FROM companies
        """).fetchone()

    return row["total"]