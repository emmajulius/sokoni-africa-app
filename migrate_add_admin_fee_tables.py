"""
Database migration script to add admin fee collection and cashout tables.

Usage:
    python migrate_add_admin_fee_tables.py
"""

from sqlalchemy import create_engine, text
from config import settings


def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database"""
    result = conn.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = :table_name
            """
        ),
        {"table_name": table_name}
    )
    return result.first() is not None


def create_admin_fee_collections_table(conn):
    """Create admin_fee_collections table if it doesn't exist"""
    if table_exists(conn, "admin_fee_collections"):
        print("✓ admin_fee_collections table already exists.")
        return
    
    print("Creating admin_fee_collections table...")
    conn.execute(
        text("""
            CREATE TABLE admin_fee_collections (
                id SERIAL PRIMARY KEY,
                order_id INTEGER NOT NULL,
                processing_fee DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                shipping_fee DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
                total_fee DOUBLE PRECISION NOT NULL,
                collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_fee_collections_order_id ON admin_fee_collections(order_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_fee_collections_collected_at ON admin_fee_collections(collected_at)"))
    conn.commit()
    print("✅ admin_fee_collections table created successfully.")


def create_admin_cashouts_table(conn):
    """Create admin_cashouts table if it doesn't exist"""
    if table_exists(conn, "admin_cashouts"):
        print("✓ admin_cashouts table already exists.")
        return
    
    print("Creating admin_cashouts table...")
    conn.execute(
        text("""
            CREATE TABLE admin_cashouts (
                id SERIAL PRIMARY KEY,
                amount DOUBLE PRECISION NOT NULL,
                payout_method VARCHAR NOT NULL,
                payout_account VARCHAR NOT NULL,
                payout_account_name VARCHAR,
                status VARCHAR NOT NULL DEFAULT 'pending',
                notes TEXT,
                rejection_reason TEXT,
                processed_by INTEGER,
                processed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (processed_by) REFERENCES users(id)
            )
        """)
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_cashouts_status ON admin_cashouts(status)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_admin_cashouts_created_at ON admin_cashouts(created_at)"))
    conn.commit()
    print("✅ admin_cashouts table created successfully.")


def run_migration():
    """Run the migration"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            create_admin_fee_collections_table(conn)
            create_admin_cashouts_table(conn)
            print("\n✅ Migration completed successfully!")
        except Exception as e:
            print(f"\n❌ Error during migration: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    try:
        print("Starting migration to add admin fee tables...")
        print(f"Database: {settings.DATABASE_URL}")
        run_migration()
    except Exception as exc:
        print(f"❌ Error running migration: {exc}")
        import traceback
        traceback.print_exc()

