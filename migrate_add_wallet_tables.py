"""
Migration script to create wallet tables
Run this script to add wallet and wallet_transactions tables to the database
"""
import psycopg2
from config import settings
import os

def migrate_wallet_tables():
    """Create wallet and wallet_transactions tables"""
    
    # Get database URL
    database_url = settings.DATABASE_URL
    
    # Parse database URL
    # Format: postgresql://user:password@host:port/database
    if database_url.startswith("postgresql://"):
        url_parts = database_url.replace("postgresql://", "").split("/")
        auth_part = url_parts[0]
        database = url_parts[1] if len(url_parts) > 1 else "sokoni_africa"
        
        auth_parts = auth_part.split("@")
        if len(auth_parts) == 2:
            user_pass = auth_parts[0].split(":")
            user = user_pass[0]
            password = ":".join(user_pass[1:]) if len(user_pass) > 1 else ""
            host_port = auth_parts[1].split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 5432
        else:
            raise ValueError("Invalid database URL format")
    else:
        raise ValueError("Only PostgreSQL is supported")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Creating wallet tables...")
        
        # Create WalletTransactionType enum if it doesn't exist
        cursor.execute("""
            DO $$ BEGIN
                CREATE TYPE wallettransactiontype AS ENUM ('topup', 'cashout', 'purchase', 'earn', 'refund', 'fee');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        
        # Create WalletTransactionStatus enum if it doesn't exist
        cursor.execute("""
            DO $$ BEGIN
                CREATE TYPE wallettransactionstatus AS ENUM ('pending', 'completed', 'failed', 'cancelled');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        
        # Create wallets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                sokocoin_balance DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                total_earned DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                total_spent DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                total_topup DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                total_cashout DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """)
        
        # Create index on user_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets(user_id);
        """)
        
        # Create wallet_transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id SERIAL PRIMARY KEY,
                wallet_id INTEGER NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                transaction_type wallettransactiontype NOT NULL,
                status wallettransactionstatus NOT NULL DEFAULT 'pending',
                sokocoin_amount DOUBLE PRECISION NOT NULL,
                local_currency_amount DOUBLE PRECISION,
                local_currency_code VARCHAR(10),
                exchange_rate DOUBLE PRECISION,
                payment_gateway VARCHAR(50),
                payment_reference VARCHAR(255),
                gateway_transaction_id VARCHAR(255),
                payout_method VARCHAR(50),
                payout_account VARCHAR(255),
                payout_reference VARCHAR(255),
                description TEXT,
                extra_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP WITH TIME ZONE
            );
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_wallet_id ON wallet_transactions(wallet_id);
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user_id ON wallet_transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_type ON wallet_transactions(transaction_type);
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_status ON wallet_transactions(status);
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_payment_ref ON wallet_transactions(payment_reference);
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_gateway_id ON wallet_transactions(gateway_transaction_id);
            CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions(created_at);
        """)
        
        print("Wallet tables created successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating wallet tables: {str(e)}")
        raise


if __name__ == "__main__":
    migrate_wallet_tables()

