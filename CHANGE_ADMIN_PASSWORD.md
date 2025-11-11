# How to Change Admin Password

## ✅ Method 1: Using Script (Recommended)

### Step 1: Update .env File

Make sure your local `.env` file has the external database URL:

```env
DATABASE_URL=postgresql://sokoni_database_mzl1_user:TyFRQ3OcwlI3G5VfhI7tMjLW2UuM69RL@dpg-d49hi9ali9vc739rodng-a.frankfurt-postgres.render.com:5432/sokoni_database_mzl1
SECRET_KEY=p1WCOZOhY7FMzewl_t8Z_bHy0m3cBgn4O7vRMJP67Eo
ALGORITHM=HS256
```

### Step 2: Run the Script

Open PowerShell in your `africa_sokoni_app_backend` folder:

```powershell
python change_admin_credentials.py
```

### Step 3: Follow Prompts

The script will ask:
1. **What do you want to change?**
   - Option 1: Change password only
   - Option 2: Change username and password
   - Option 3: Change email and password
   - Option 4: Change username, email, and password

2. **Enter new password** (twice for confirmation)

3. **Enter new username/email** (if changing)

### Step 4: Done!

The script will update the password in the database. You can now login with the new password.

---

## ✅ Method 2: Direct Database Update (Advanced)

If you prefer SQL:

```powershell
# Connect to database and update password directly
python -c "
from database import SessionLocal
from models import User
from auth import get_password_hash

db = SessionLocal()
admin = db.query(User).filter(User.username == 'admin').first()
if admin:
    new_password = input('Enter new password: ')
    admin.hashed_password = get_password_hash(new_password)
    db.commit()
    print('✅ Password updated!')
else:
    print('❌ Admin user not found')
db.close()
"
```

---

## 📋 Quick Command Reference

### Change Password Only:
```powershell
python change_admin_credentials.py
# Select option 1
# Enter new password
```

### Change Username and Password:
```powershell
python change_admin_credentials.py
# Select option 2
# Enter new username
# Enter new password
```

### Change Email and Password:
```powershell
python change_admin_credentials.py
# Select option 3
# Enter new email
# Enter new password
```

---

## 🎯 After Changing Password

1. **Test login** at: `https://sokoni-africa-app.onrender.com/admin/login`
2. **Use new password** to login
3. **Old password** will no longer work

---

## ⚠️ Important Notes

- **Password is hashed** - Can't be recovered, only reset
- **Changes are immediate** - No restart needed
- **Works with Render database** - Script connects to your Render PostgreSQL
- **No redeploy needed** - Changes are in database, not code

---

## 🆘 Troubleshooting

### "Admin user not found"
- Make sure you ran `create_admin_user.py` first
- Check username is `admin` (or whatever you set)

### "Connection failed"
- Verify `.env` file has correct `DATABASE_URL`
- Use external database URL (frankfurt-postgres, not oregon)
- Make sure SSL is working (code handles this automatically)

### "Module not found"
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the correct directory

---

## ✅ Quick Steps Summary

1. **Update `.env`** with external database URL
2. **Run**: `python change_admin_credentials.py`
3. **Select option 1** (change password only)
4. **Enter new password** (twice)
5. **Done!** Login with new password

