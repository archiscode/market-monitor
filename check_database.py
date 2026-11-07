from src.database import get_connection


with get_connection() as connection:
    tables = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
    """).fetchall()

    for table in tables:
        print(f"\nTable: {table['name']}")

        columns = connection.execute(
            f"PRAGMA table_info({table['name']})"
        ).fetchall()

        for column in columns:
            print(f"  - {column['name']}")