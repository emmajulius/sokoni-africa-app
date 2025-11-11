# How to Change Admin Credentials

This guide explains how to change the admin panel credentials for the Sokoni Africa application.

## Overview

Admin credentials are stored in two places:
1. **Database**: The actual user account in the database
2. **Environment Variables** (optional): Used to determine which user is considered an admin

## Method 1: Using the Script (Recommended)

The easiest way to change admin credentials is to use the provided script:

```bash
python change_admin_credentials.py
```

This script will:
- Find the current admin user
- Allow you to change password, username, and/or email
- Update the database
- Provide instructions for updating environment variables

### Steps:

1. **Run the script**:
   ```bash
   cd africa_sokoni_app_backend
   python change_admin_credentials.py
   ```

2. **Follow the prompts**:
   - Choose what you want to change (password, username, email, or all)
   - Enter the new values
   - Confirm the changes

3. **Update environment variables** (if needed):
   - Open your `.env` file
   - Update `ADMIN_USERNAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` if you changed them
   - Example:
     ```env
     ADMIN_USERNAME=new_admin_username
     ADMIN_EMAIL=new_admin@example.com
     ADMIN_PASSWORD=your_new_password
     ```

4. **Restart the server**:
   ```bash
   # Stop the server (Ctrl+C)
   # Start it again
   uvicorn main:app --reload
   ```

5. **Login with new credentials**:
   - Go to: `http://localhost:8000/admin/login`
   - Use your new username/email and password

## Method 2: Manual Database Update

If you prefer to update the database directly:

### Step 1: Update the Database

You can use Python to update the admin user directly:

```python
from database import SessionLocal
from models import User
from auth import get_password_hash

db = SessionLocal()

# Find the admin user
admin_user = db.query(User).filter(
    User.username == "admin"  # or your admin username
).first()

# Update password
admin_user.hashed_password = get_password_hash("new_password_here")

# Update username (optional)
admin_user.username = "new_username"

# Update email (optional)
admin_user.email = "new_email@example.com"

db.commit()
db.close()
```

### Step 2: Update Environment Variables

Update your `.env` file:

```env
ADMIN_USERNAME=new_username
ADMIN_EMAIL=new_email@example.com
ADMIN_PASSWORD=new_password_here
```

### Step 3: Restart Server

Restart your FastAPI server for changes to take effect.

## Method 3: Using Environment Variables Only

If you only want to change the password and keep using environment variables:

### Step 1: Update .env File

```env
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@sokoniafrica.com
ADMIN_PASSWORD=your_new_secure_password
```

### Step 2: Update Database Password

Run the script or use Python:

```python
from database import SessionLocal
from models import User
from auth import get_password_hash
import os

db = SessionLocal()
admin_username = os.getenv("ADMIN_USERNAME", "admin")

admin_user = db.query(User).filter(User.username == admin_username).first()
admin_user.hashed_password = get_password_hash(os.getenv("ADMIN_PASSWORD", "admin123"))

db.commit()
db.close()
```

### Step 3: Restart Server

Restart your FastAPI server.

## How Admin Authentication Works

The admin panel checks if a user is an admin by:

1. **Username match**: User's username matches `ADMIN_USERNAME` environment variable
2. **Email match**: User's email matches `ADMIN_EMAIL` environment variable

Then it verifies the password from the database.

## Important Notes

1. **Security**: Always use strong passwords in production!
2. **Environment Variables**: If you change the username or email, make sure to update the environment variables to match
3. **Database**: The actual credentials are stored in the database. Environment variables are only used to identify which user is the admin
4. **Server Restart**: After changing credentials, you must restart the server for environment variable changes to take effect
5. **Multiple Admins**: Currently, only one user can be an admin (matching ADMIN_USERNAME or ADMIN_EMAIL). To support multiple admins, you would need to modify the `is_admin_user()` function in `app/routers/admin.py`

## Troubleshooting

### "Admin user not found"
- Run `python create_admin_user.py` first to create an admin user
- Check that your `.env` file has the correct `ADMIN_USERNAME` or `ADMIN_EMAIL`

### "Invalid credentials" after changing password
- Make sure you updated the database password (not just environment variables)
- Restart the server after changing environment variables
- Verify the username/email matches what's in the database

### "Access denied" after login
- Check that the user's username or email matches `ADMIN_USERNAME` or `ADMIN_EMAIL` in your `.env` file
- Verify the user exists in the database
- Make sure the user's `is_active` field is `True`

## Example: Complete Credential Change

```bash
# 1. Run the script
python change_admin_credentials.py

# 2. Choose option 4 (change username, email, and password)
# 3. Enter:
#    - New username: myadmin
#    - New email: myadmin@example.com
#    - New password: SecurePass123!

# 4. Update .env file:
ADMIN_USERNAME=myadmin
ADMIN_EMAIL=myadmin@example.com
ADMIN_PASSWORD=SecurePass123!

# 5. Restart server
uvicorn main:app --reload

# 6. Login at http://localhost:8000/admin/login
#    Username: myadmin
#    Password: SecurePass123!
```

## Support

If you encounter any issues, check:
1. Database connection is working
2. User exists in the database
3. Environment variables are set correctly
4. Server has been restarted after changes
5. Password is at least 6 characters long

