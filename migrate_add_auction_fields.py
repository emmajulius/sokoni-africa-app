"""
Migration script to add auction fields to products table and create bids table.
Run this script to add auction functionality to the database.

Usage:
    python migrate_add_auction_fields.py
"""

import psycopg2
from psycopg2 import sql
import os
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

def migrate():
    """Add auction fields to products table and create bids table"""
    conn = None
    try:
        # Parse DATABASE_URL (handles URL-encoded passwords)
        # Format: postgresql://user:password@host:port/database
        parsed = urlparse(DATABASE_URL)
        
        user = unquote(parsed.username) if parsed.username else None
        password = unquote(parsed.password) if parsed.password else None
        host = parsed.hostname
        port = parsed.port or 5432
        database = parsed.path.lstrip('/')
        
        if not all([user, password, host, database]):
            raise ValueError("Invalid DATABASE_URL format. Required: postgresql://user:password@host:port/database")
        
        print(f"Connecting to database: {host}:{port}/{database} as user: {user}")
        
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = False
        cur = conn.cursor()
        
        print("Starting migration: Adding auction fields...")
        
        # Add auction fields to products table
        print("1. Adding auction fields to products table...")
        cur.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS is_auction BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS starting_price DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS bid_increment DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS auction_duration_hours INTEGER,
            ADD COLUMN IF NOT EXISTS auction_start_time TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS auction_end_time TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS current_bid DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS current_bidder_id INTEGER REFERENCES users(id),
            ADD COLUMN IF NOT EXISTS auction_status VARCHAR DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS winner_id INTEGER REFERENCES users(id),
            ADD COLUMN IF NOT EXISTS winner_paid BOOLEAN DEFAULT FALSE;
        """)
        
        # Create indexes for auction fields
        print("2. Creating indexes for auction fields...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_is_auction ON products(is_auction);
            CREATE INDEX IF NOT EXISTS idx_products_auction_status ON products(auction_status);
            CREATE INDEX IF NOT EXISTS idx_products_auction_end_time ON products(auction_end_time);
            CREATE INDEX IF NOT EXISTS idx_products_current_bidder_id ON products(current_bidder_id);
            CREATE INDEX IF NOT EXISTS idx_products_winner_id ON products(winner_id);
        """)
        
        # Create bids table
        print("3. Creating bids table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                bidder_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                bid_amount DOUBLE PRECISION NOT NULL,
                bid_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                is_winning_bid BOOLEAN DEFAULT FALSE,
                is_outbid BOOLEAN DEFAULT FALSE
            );
        """)
        
        # Create indexes for bids table
        print("4. Creating indexes for bids table...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bids_product_id ON bids(product_id);
            CREATE INDEX IF NOT EXISTS idx_bids_bidder_id ON bids(bidder_id);
            CREATE INDEX IF NOT EXISTS idx_bids_bid_time ON bids(bid_time);
            CREATE INDEX IF NOT EXISTS idx_bids_is_winning_bid ON bids(is_winning_bid);
        """)
        
        # Commit transaction
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify the changes
        print("\n📊 Verifying migration...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'products' 
            AND column_name IN ('is_auction', 'starting_price', 'bid_increment', 'auction_duration_hours', 
                                'auction_start_time', 'auction_end_time', 'current_bid', 'current_bidder_id', 
                                'auction_status', 'winner_id', 'winner_paid')
            ORDER BY column_name;
        """)
        product_columns = cur.fetchall()
        print(f"   ✓ Found {len(product_columns)} auction columns in products table")
        
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'bids';
        """)
        bids_table = cur.fetchone()
        if bids_table:
            print("   ✓ Bids table created successfully")
            
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'bids'
                ORDER BY column_name;
            """)
            bids_columns = cur.fetchall()
            print(f"   ✓ Bids table has {len(bids_columns)} columns")
        else:
            print("   ⚠️  Warning: Bids table not found")
        
        print("\n✅ All database changes verified successfully!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    migrate()

