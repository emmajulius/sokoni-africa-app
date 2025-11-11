"""
Script to create an admin user for the admin panel.

Usage:
    python create_admin_user.py

This will create an admin user with:
- Username: admin (or from ADMIN_USERNAME env var)
- Email: admin@sokoniafrica.com (or from ADMIN_EMAIL env var)
- Password: admin123 (or from ADMIN_PASSWORD env var)

⚠️ IMPORTANT: Change the password after first login!
"""

import os
import sys
from database import SessionLocal
from models import User, UserType
from auth import get_password_hash

def create_admin_user():
    """Create an admin user"""
    db = SessionLocal()
    
    try:
        # Get admin credentials from environment or use defaults
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@sokoniafrica.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        # Check if admin user already exists
        existing_user = db.query(User).filter(
            (User.username == admin_username) | 
            (User.email == admin_email)
        ).first()
        
        if existing_user:
            print(f"⚠️  Admin user already exists!")
            print(f"   Username: {existing_user.username}")
            print(f"   Email: {existing_user.email}")
            print(f"   ID: {existing_user.id}")
            
            # Update password if needed
            response = input("\nDo you want to update the password? (y/n): ")
            if response.lower() == 'y':
                existing_user.hashed_password = get_password_hash(admin_password)
                db.commit()
                print(f"✅ Password updated!")
            else:
                print("Skipped password update.")
            
            db.close()
            return
        
        # Create new admin user
        admin_user = User(
            username=admin_username,
            email=admin_email,
            full_name="Admin User",
            hashed_password=get_password_hash(admin_password),
            user_type=UserType.CLIENT,  # Can be any type
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"\n📋 Admin Credentials:")
        print(f"   Username: {admin_username}")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   User ID: {admin_user.id}")
        print(f"\n🌐 Access admin panel at: http://localhost:8000/admin/login")
        print(f"\n⚠️  IMPORTANT: Change the password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()

