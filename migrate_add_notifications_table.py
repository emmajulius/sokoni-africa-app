from sqlalchemy import create_engine, text
from config import settings

def create_notifications_table():
    """Create notifications table if it doesn't exist"""
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # Check if table exists
        check_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'notifications'
            );
        """)
        result = conn.execute(check_query)
        table_exists = result.scalar()
        
        if not table_exists:
            print("Creating notifications table...")
            conn.execute(text("""
                CREATE TABLE notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    notification_type VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    related_user_id INTEGER,
                    related_product_id INTEGER,
                    related_order_id INTEGER,
                    related_conversation_id INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id),
                    CONSTRAINT fk_notifications_related_user FOREIGN KEY (related_user_id) REFERENCES users(id),
                    CONSTRAINT fk_notifications_related_product FOREIGN KEY (related_product_id) REFERENCES products(id)
                );
            """))
            
            # Create indexes
            conn.execute(text("CREATE INDEX idx_notifications_user_id ON notifications(user_id);"))
            conn.execute(text("CREATE INDEX idx_notifications_is_read ON notifications(is_read);"))
            conn.execute(text("CREATE INDEX idx_notifications_created_at ON notifications(created_at);"))
            
            conn.commit()
            print("✓ Created notifications table with indexes")
        else:
            print("✓ notifications table already exists")
        
        print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    try:
        print("Starting migration to create notifications table...")
        print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Unknown'}\n")
        create_notifications_table()
    except Exception as e:
        print(f"❌ Error running migration: {e}")
        import traceback
        traceback.print_exc()

