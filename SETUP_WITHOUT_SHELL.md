# Setup Database Without Render Shell (Free Plan)

Since Render's shell is not available on the free plan, we'll run setup scripts **locally** but connect to your **Render database**.

---

## ✅ Step 1: Get Your Database URL

1. Go to Render Dashboard
2. Click your **PostgreSQL** service (not the web service)
3. Go to **"Info"** or **"Connections"** tab
4. Copy the **"Internal Database URL"**
   - Format: `postgresql://user:pass@host:5432/dbname`

**OR** use the one from your environment variables:
- `postgresql://sokoni_database_mzl1_user:TyFRQ3OcwlI3G5VfhI7tMjLW2UuM69RL@dpg-d49hi9ali9vc739rodng-a.oregon-postgres.render.com:5432/sokoni_database_mzl1`

---

## ✅ Step 2: Create Local .env File

1. In your local `africa_sokoni_app_backend` folder
2. Create/update `.env` file with:

```env
DATABASE_URL=postgresql://sokoni_database_mzl1_user:TyFRQ3OcwlI3G5VfhI7tMjLW2UuM69RL@dpg-d49hi9ali9vc739rodng-a.oregon-postgres.render.com:5432/sokoni_database_mzl1
SECRET_KEY=p1WCOZOhY7FMzewl_t8Z_bHy0m3cBgn4O7vRMJP67Eo
ALGORITHM=HS256
```

**Important**: Use the **Internal Database URL** (not external), as it's faster and more reliable.

---

## ✅ Step 3: Run Setup Scripts Locally

Open PowerShell/Terminal in your `africa_sokoni_app_backend` folder:

### Initialize Database:
```powershell
python init_db.py
```

### Run Migrations (if needed):
```powershell
python migrate_add_admin_fee_tables.py
python migrate_add_currency_to_admin_cashouts.py
python migrate_add_bank_details_to_admin_cashouts.py
```

### Create Admin User:
```powershell
python create_admin_user.py
```
- Follow prompts to set username, email, and password
- Remember these credentials!

---

## ✅ Step 4: Verify Setup

### Test Database Connection:
```powershell
python -c "from database import engine; from sqlalchemy import inspect; inspector = inspect(engine); print('Tables:', inspector.get_table_names())"
```

Should show all your tables.

---

## ✅ Step 5: Test Admin Panel

1. Visit: `https://sokoni-africa-app.onrender.com/admin/login`
2. Login with admin credentials you just created
3. Should work!

---

## 🔧 Alternative: Create Setup API Endpoints

If you prefer, we can create API endpoints for setup (one-time use, then disable):

1. `/api/setup/init-db` - Initialize database
2. `/api/setup/create-admin` - Create admin user

But running locally is **safer** and **recommended**.

---

## ⚠️ Important Notes

### Database URL
- Use **Internal Database URL** from Render PostgreSQL
- It's faster and more reliable than external URL
- Format: `postgresql://user:pass@host:5432/dbname`

### Security
- Never commit `.env` file to Git
- Keep database credentials secret
- Only run setup scripts from trusted machines

### Connection
- Your local machine connects directly to Render's database
- No need for VPN or special setup
- Just need the database URL

---

## 🎯 Quick Checklist

- [ ] Get Internal Database URL from Render
- [ ] Create local `.env` file with DATABASE_URL
- [ ] Run `python init_db.py`
- [ ] Run migration scripts (if any)
- [ ] Run `python create_admin_user.py`
- [ ] Test admin panel login
- [ ] Verify everything works

---

## 🆘 Troubleshooting

### "Connection refused"
- Check database URL is correct
- Verify PostgreSQL service is running in Render
- Try using Internal Database URL (not external)

### "Module not found"
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in the correct directory

### "Table already exists"
- Database might already be initialized
- Skip `init_db.py` and just run migrations

---

## ✅ After Setup

Once database is initialized and admin user is created:
- Admin panel will work
- API endpoints will work
- Mobile app can connect
- Everything is ready!

