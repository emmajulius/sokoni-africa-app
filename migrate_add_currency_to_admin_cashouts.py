"""
Database migration script to add currency fields to admin_cashouts table.

Usage:
    python migrate_add_currency_to_admin_cashouts.py
"""

from sqlalchemy import create_engine, text
from config import settings


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    result = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name}
    )
    return result.first() is not None


def add_currency_columns(conn):
    """Add currency, local_currency_amount, and exchange_rate columns to admin_cashouts table"""
    if not column_exists(conn, "admin_cashouts", "currency"):
        print("Adding currency column to admin_cashouts table...")
        conn.execute(
            text("ALTER TABLE admin_cashouts ADD COLUMN currency VARCHAR")
        )
        print("✅ currency column added successfully.")
    else:
        print("✓ currency column already exists.")
    
    if not column_exists(conn, "admin_cashouts", "local_currency_amount"):
        print("Adding local_currency_amount column to admin_cashouts table...")
        conn.execute(
            text("ALTER TABLE admin_cashouts ADD COLUMN local_currency_amount DOUBLE PRECISION")
        )
        print("✅ local_currency_amount column added successfully.")
    else:
        print("✓ local_currency_amount column already exists.")
    
    if not column_exists(conn, "admin_cashouts", "exchange_rate"):
        print("Adding exchange_rate column to admin_cashouts table...")
        conn.execute(
            text("ALTER TABLE admin_cashouts ADD COLUMN exchange_rate DOUBLE PRECISION")
        )
        print("✅ exchange_rate column added successfully.")
    else:
        print("✓ exchange_rate column already exists.")
    
    conn.commit()


def run_migration():
    """Run the migration"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            add_currency_columns(conn)
            print("\n✅ Migration completed successfully!")
        except Exception as e:
            print(f"\n❌ Error during migration: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    try:
        print("Starting migration to add currency fields to admin_cashouts table...")
        print(f"Database: {settings.DATABASE_URL}")
        run_migration()
    except Exception as exc:
        print(f"❌ Error running migration: {exc}")
        import traceback
        traceback.print_exc()

