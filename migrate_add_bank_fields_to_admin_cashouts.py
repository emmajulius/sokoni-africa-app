"""
Database migration script to add bank transfer fields to admin_cashouts table.

Usage:
    python migrate_add_bank_fields_to_admin_cashouts.py
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


def add_bank_fields(conn):
    """Add bank transfer fields to admin_cashouts table"""
    fields = [
        ("bank_name", "VARCHAR"),
        ("bank_account_number", "VARCHAR"),
        ("bank_account_holder", "VARCHAR"),
        ("bank_branch", "VARCHAR"),
        ("bank_swift_code", "VARCHAR")
    ]
    
    for field_name, field_type in fields:
        if not column_exists(conn, "admin_cashouts", field_name):
            print(f"Adding {field_name} column to admin_cashouts table...")
            conn.execute(
                text(f"ALTER TABLE admin_cashouts ADD COLUMN {field_name} {field_type}")
            )
            print(f"✅ {field_name} column added successfully.")
        else:
            print(f"✓ {field_name} column already exists.")
    
    conn.commit()


def run_migration():
    """Run the migration"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            add_bank_fields(conn)
            print("\n✅ Migration completed successfully!")
        except Exception as e:
            print(f"\n❌ Error during migration: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    try:
        print("Starting migration to add bank fields to admin_cashouts table...")
        print(f"Database: {settings.DATABASE_URL}")
        run_migration()
    except Exception as exc:
        print(f"❌ Error running migration: {exc}")
        import traceback
        traceback.print_exc()
