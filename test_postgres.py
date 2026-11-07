
import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def test_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in .env")

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            result = cursor.fetchone()

    print("PostgreSQL connection successful.")
    print(result[0])


if __name__ == "__main__":
    test_connection()
