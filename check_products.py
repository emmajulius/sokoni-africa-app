"""
Test script to check products in database
Run this to see what products exist in the database
"""
import psycopg2
from config import settings

def check_products():
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        
        # Check total products
        cur.execute('SELECT COUNT(*) FROM products')
        count = cur.fetchone()[0]
        print(f"\n{'='*60}")
        print(f"DATABASE PRODUCT CHECK")
        print(f"{'='*60}")
        print(f"Total products in database: {count}")
        print(f"{'='*60}\n")
        
        if count > 0:
            # Get sample products
            cur.execute('SELECT id, title, price, category, seller_id, created_at FROM products ORDER BY created_at DESC LIMIT 10')
            rows = cur.fetchall()
            
            print("Sample products:")
            for row in rows:
                print(f"  ID: {row[0]}, Title: {row[1]}, Price: {row[2]}, Category: {row[3]}, Seller: {row[4]}, Created: {row[5]}")
        else:
            print("WARNING: No products found in database!")
            print("\nPossible reasons:")
            print("  1. Products were created but transaction not committed")
            print("  2. Products created in different database")
            print("  3. Products were deleted")
            print("  4. Database connection issue")
        
        # Check users
        cur.execute('SELECT COUNT(*) FROM users')
        user_count = cur.fetchone()[0]
        print(f"\nTotal users in database: {user_count}")
        
        # Check categories
        cur.execute('SELECT COUNT(*) FROM categories')
        cat_count = cur.fetchone()[0]
        print(f"Total categories in database: {cat_count}")
        
        if cat_count > 0:
            cur.execute('SELECT slug, name FROM categories LIMIT 5')
            cats = cur.fetchall()
            print("\nAvailable categories:")
            for cat in cats:
                print(f"  - {cat[1]} (slug: {cat[0]})")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_products()
