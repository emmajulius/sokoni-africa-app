"""
Database migration script to add processing_fee column to orders table.

Usage:
    python migrate_add_processing_fee.py
"""

from sqlalchemy import create_engine, text
from config import settings


def add_processing_fee_column():
    """Add processing_fee column to orders table if missing."""
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='orders' AND column_name='processing_fee'
                """
            )
        )
        column_exists = result.first() is not None

        if column_exists:
            print("✓ processing_fee column already exists on orders table.")
            return

        print("Adding processing_fee column to orders table...")
        conn.execute(
            text("ALTER TABLE orders ADD COLUMN processing_fee DOUBLE PRECISION DEFAULT 0")
        )
        conn.commit()
        print("✅ processing_fee column added successfully.")


if __name__ == "__main__":
    try:
        print("Starting migration to add processing_fee to orders table...")
        print(f"Database: {settings.DATABASE_URL}")
        add_processing_fee_column()
    except Exception as exc:
        print(f"❌ Error running migration: {exc}")

