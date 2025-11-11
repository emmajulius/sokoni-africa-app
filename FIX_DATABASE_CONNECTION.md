# Fix Database Connection from Local Machine

## Problem

Two issues:
1. **"password authentication failed"** - Password might be wrong
2. **"SSL/TLS required"** - External connections need SSL

---

## ✅ Solution: Use External Database URL with SSL

### Step 1: Get External Database URL

1. Go to Render Dashboard
2. Click your **PostgreSQL** service
3. Go to **"Info"** or **"Connections"** tab
4. Look for **"External Database URL"** (different from Internal)
5. Copy it

**OR** if you only see Internal URL, add SSL parameters:

---

### Step 2: Update .env File with SSL

If you only have the Internal URL, modify it to include SSL:

**Current (Internal URL - doesn't work from local):**
```
postgresql://sokoni_database_mzl1_user:TyFRQ3OcwlI3G5VfhI7tMjLW2UuM69RL@dpg-d49hi9ali9vc739rodng-a.oregon-postgres.render.com:5432/sokoni_database_mzl1
```

**Updated (with SSL - works from local):**
```
postgresql://sokoni_database_mzl1_user:TyFRQ3OcwlI3G5VfhI7tMjLW2UuM69RL@dpg-d49hi9ali9vc739rodng-a.oregon-postgres.render.com:5432/sokoni_database_mzl1?sslmode=require
```

**Add `?sslmode=require` at the end!**

---

### Step 3: Verify Password

The password might have changed. To reset:

1. Render Dashboard → PostgreSQL service
2. **Settings** tab
3. Look for **"Reset Password"** or **"Change Password"**
4. Reset it
5. Update your `.env` file with new password

---

## 🔧 Alternative: Use External Database URL

Render provides two URLs:
- **Internal Database URL**: For services within Render (faster, no SSL needed)
- **External Database URL**: For connections from outside Render (requires SSL)

**Get the External URL:**
1. PostgreSQL service → **Info** tab
2. Look for **"External Database URL"**
3. It should already include SSL parameters
4. Use this in your local `.env` file

---

## ✅ Updated .env File

```env
DATABASE_URL=postgresql://sokoni_database_mzl1_user:TyFRQ3OcwlI3G5VfhI7tMjLW2UuM69RL@dpg-d49hi9ali9vc739rodng-a.oregon-postgres.render.com:5432/sokoni_database_mzl1?sslmode=require
SECRET_KEY=p1WCOZOhY7FMzewl_t8Z_bHy0m3cBgn4O7vRMJP67Eo
ALGORITHM=HS256
```

**Key change**: Added `?sslmode=require` at the end

---

## 🧪 Test Connection

After updating `.env`, test:

```powershell
python -c "from database import engine; from sqlalchemy import inspect; inspector = inspect(engine); print('✅ Connected! Tables:', inspector.get_table_names())"
```

Should show tables or "Connected!" message.

---

## 🆘 If Still Fails

### Option 1: Reset Database Password

1. Render Dashboard → PostgreSQL → Settings
2. Reset password
3. Update `.env` with new password
4. Also update in Render Web Service environment variables

### Option 2: Check Firewall

Render PostgreSQL might block external connections. Check:
- PostgreSQL Settings → **"Allow connections from"**
- Make sure external connections are allowed

### Option 3: Use pgAdmin or DBeaver

Test connection with a database client first to verify credentials work.

---

## 📋 Quick Fix Steps

1. **Add SSL to connection string**: `?sslmode=require`
2. **Update `.env` file**
3. **Try connection again**
4. **If fails, reset password in Render**
5. **Update both local `.env` and Render environment variables**

