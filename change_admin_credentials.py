"""
Script to change admin credentials for the admin panel.

Usage:
    python change_admin_credentials.py

This script allows you to:
1. Change the admin password
2. Change the admin username (optional)
3. Change the admin email (optional)

⚠️ IMPORTANT: After changing credentials, update your .env file and restart the server!
"""

import os
import sys
import getpass
from database import SessionLocal
from models import User
from auth import get_password_hash, verify_password

def change_admin_credentials():
    """Change admin user credentials"""
    db = SessionLocal()
    
    try:
        # Get current admin credentials from environment or use defaults
        current_admin_username = os.getenv("ADMIN_USERNAME", "admin")
        current_admin_email = os.getenv("ADMIN_EMAIL", "admin@sokoniafrica.com")
        
        print("=" * 60)
        print("🔐 CHANGE ADMIN CREDENTIALS")
        print("=" * 60)
        print(f"\nCurrent admin username: {current_admin_username}")
        print(f"Current admin email: {current_admin_email}")
        print("\n" + "-" * 60)
        
        # Find the admin user
        admin_user = db.query(User).filter(
            (User.username == current_admin_username) | 
            (User.email == current_admin_email)
        ).first()
        
        if not admin_user:
            print(f"❌ Admin user not found!")
            print(f"   Please run 'python create_admin_user.py' first to create an admin user.")
            db.close()
            sys.exit(1)
        
        print(f"\n✅ Admin user found:")
        print(f"   ID: {admin_user.id}")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email or 'Not set'}")
        print(f"   Full Name: {admin_user.full_name or 'Not set'}")
        print("\n" + "-" * 60)
        
        # Ask what to change
        print("\nWhat would you like to change?")
        print("1. Change password only")
        print("2. Change username and password")
        print("3. Change email and password")
        print("4. Change username, email, and password")
        print("5. Cancel")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "5":
            print("Cancelled.")
            db.close()
            return
        
        new_username = admin_user.username
        new_email = admin_user.email
        new_password = None
        
        # Get new username if needed
        if choice in ["2", "4"]:
            new_username = input("\nEnter new username: ").strip()
            if not new_username:
                print("❌ Username cannot be empty!")
                db.close()
                sys.exit(1)
            
            # Check if username already exists (for another user)
            existing_user = db.query(User).filter(
                User.username == new_username,
                User.id != admin_user.id
            ).first()
            if existing_user:
                print(f"❌ Username '{new_username}' is already taken by another user!")
                db.close()
                sys.exit(1)
        
        # Get new email if needed
        if choice in ["3", "4"]:
            new_email = input("\nEnter new email: ").strip()
            if not new_email:
                print("❌ Email cannot be empty!")
                db.close()
                sys.exit(1)
            
            # Check if email already exists (for another user)
            existing_user = db.query(User).filter(
                User.email == new_email,
                User.id != admin_user.id
            ).first()
            if existing_user:
                print(f"❌ Email '{new_email}' is already taken by another user!")
                db.close()
                sys.exit(1)
        
        # Get new password
        if choice in ["1", "2", "3", "4"]:
            new_password = getpass.getpass("\nEnter new password: ").strip()
            if not new_password:
                print("❌ Password cannot be empty!")
                db.close()
                sys.exit(1)
            
            if len(new_password) < 6:
                print("❌ Password must be at least 6 characters long!")
                db.close()
                sys.exit(1)
            
            confirm_password = getpass.getpass("Confirm new password: ").strip()
            if new_password != confirm_password:
                print("❌ Passwords do not match!")
                db.close()
                sys.exit(1)
        
        # Update the user
        if choice in ["2", "4"]:
            admin_user.username = new_username
            print(f"✅ Username updated to: {new_username}")
        
        if choice in ["3", "4"]:
            admin_user.email = new_email
            print(f"✅ Email updated to: {new_email}")
        
        if new_password:
            admin_user.hashed_password = get_password_hash(new_password)
            print(f"✅ Password updated")
        
        db.commit()
        db.refresh(admin_user)
        
        print("\n" + "=" * 60)
        print("✅ ADMIN CREDENTIALS UPDATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📋 Updated Admin Credentials:")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email or 'Not set'}")
        print(f"   Password: {'*' * len(new_password) if new_password else 'Not changed'}")
        print(f"   User ID: {admin_user.id}")
        
        print("\n" + "⚠️  IMPORTANT NEXT STEPS:")
        print("=" * 60)
        print("1. Update your .env file with the new credentials:")
        print(f"   ADMIN_USERNAME={admin_user.username}")
        print(f"   ADMIN_EMAIL={admin_user.email or current_admin_email}")
        print(f"   ADMIN_PASSWORD=<your_new_password>  # Optional, only if you want to use env var")
        print("\n2. Restart your FastAPI server for changes to take effect")
        print("\n3. Login to admin panel with the new credentials:")
        print(f"   URL: http://localhost:8000/admin/login")
        print(f"   Username/Email: {admin_user.username}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
        db.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error changing admin credentials: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    change_admin_credentials()

