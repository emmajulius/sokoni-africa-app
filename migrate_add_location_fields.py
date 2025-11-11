"""
Database migration script to add location fields to users table
Run this script to add latitude, longitude, and location_address columns to the users table.

Usage:
    python migrate_add_location_fields.py
"""

from sqlalchemy import create_engine, text
from config import settings

def add_location_columns():
    """Add location columns to users table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if columns already exist
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name IN ('latitude', 'longitude', 'location_address')
        """)
        result = conn.execute(check_query)
        existing_columns = [row[0] for row in result]
        
        # Add latitude column if it doesn't exist
        if 'latitude' not in existing_columns:
            print("Adding latitude column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN latitude FLOAT"))
            conn.commit()
            print("✓ Added latitude column")
        else:
            print("✓ latitude column already exists")
        
        # Add longitude column if it doesn't exist
        if 'longitude' not in existing_columns:
            print("Adding longitude column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN longitude FLOAT"))
            conn.commit()
            print("✓ Added longitude column")
        else:
            print("✓ longitude column already exists")
        
        # Add location_address column if it doesn't exist
        if 'location_address' not in existing_columns:
            print("Adding location_address column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN location_address VARCHAR"))
            conn.commit()
            print("✓ Added location_address column")
        else:
            print("✓ location_address column already exists")
        
        print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    try:
        print("Starting migration to add location fields to users table...")
        print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Unknown'}\n")
        add_location_columns()
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        import traceback
        traceback.print_exc()

