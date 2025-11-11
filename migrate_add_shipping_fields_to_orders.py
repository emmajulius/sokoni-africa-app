"""
Migration script to add shipping-related columns to the orders table.

Usage:
    python migrate_add_shipping_fields_to_orders.py
"""

import sys
from sqlalchemy import text
from database import engine


def column_exists(column_name: str) -> bool:
    query = text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'orders' AND column_name = :column
    """)
    with engine.connect() as connection:
        result = connection.execute(query, {"column": column_name}).fetchone()
        return result is not None


def add_column(sql: str):
    with engine.connect() as connection:
        connection.execute(text(sql))
        connection.commit()


def main():
    try:
        if not column_exists("shipping_fee"):
            print("Adding shipping_fee column to orders...")
            add_column("ALTER TABLE orders ADD COLUMN shipping_fee DOUBLE PRECISION DEFAULT 0.0;")
            print("✓ Added shipping_fee column")
        else:
            print("shipping_fee column already exists. Skipping.")

        if not column_exists("shipping_distance_km"):
            print("Adding shipping_distance_km column to orders...")
            add_column("ALTER TABLE orders ADD COLUMN shipping_distance_km DOUBLE PRECISION;")
            print("✓ Added shipping_distance_km column")
        else:
            print("shipping_distance_km column already exists. Skipping.")

        if not column_exists("includes_shipping"):
            print("Adding includes_shipping column to orders...")
            add_column("ALTER TABLE orders ADD COLUMN includes_shipping BOOLEAN DEFAULT FALSE;")
            print("✓ Added includes_shipping column")
        else:
            print("includes_shipping column already exists. Skipping.")

        print("Migration completed successfully.")
    except Exception as exc:
        print(f"Migration failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()


