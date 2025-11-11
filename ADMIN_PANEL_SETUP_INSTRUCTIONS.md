# Admin Panel Setup Instructions - Step by Step

## 📋 Prerequisites

Before starting, make sure:
1. ✅ You have Python installed
2. ✅ Your database is running (PostgreSQL)
3. ✅ Your `.env` file is configured with database credentials
4. ✅ You're in the backend directory: `africa_sokoni_app_backend`

---

## Step 1: Install Dependencies

### What this does:
Installs the required Python packages for the admin panel (Jinja2 for templates, aiofiles for file operations).

### How to do it:

**Open your terminal/command prompt** and navigate to the backend folder:

```bash
# If you're in the project root
cd sokoni_africa_app/africa_sokoni_app_backend

# Or if you're already in sokoni_africa_app
cd africa_sokoni_app_backend
```

**Then install dependencies:**

```bash
pip install -r requirements.txt
```

**What you'll see:**
```
Collecting jinja2==3.1.2
Collecting aiofiles==23.2.1
...
Successfully installed jinja2-3.1.2 aiofiles-23.2.1
```

**✅ Success indicator:** No errors, packages installed successfully.

---

## Step 2: Create Admin User

### What this does:
Creates a user account in your database that has admin privileges. This user can log into the admin panel.

### How to do it:

**Run the admin user creation script:**

```bash
python create_admin_user.py
```

**What will happen:**

**Scenario A: Admin user doesn't exist**
```
✅ Admin user created successfully!

📋 Admin Credentials:
   Username: admin
   Email: admin@sokoniafrica.com
   Password: admin123
   User ID: 1

🌐 Access admin panel at: http://localhost:8000/admin/login

⚠️  IMPORTANT: Change the password after first login!
```

**Scenario B: Admin user already exists**
```
⚠️  Admin user already exists!
   Username: admin
   Email: admin@sokoniafrica.com
   ID: 1

Do you want to update the password? (y/n):
```

If you type `y`, it will update the password. If `n`, it skips.

**✅ Success indicator:** You see the success message with credentials.

**❌ If you get an error:**
- **Database connection error**: Check your `.env` file has correct `DATABASE_URL`
- **Module not found**: Make sure you're in the `africa_sokoni_app_backend` directory
- **Permission error**: Make sure your database user has permission to create users

---

## Step 3: Start the Server

### What this does:
Starts your FastAPI backend server, which now includes the admin panel routes.

### How to do it:

**Start the server:**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**What you'll see:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**✅ Success indicator:** Server is running without errors.

**Keep this terminal open!** The server needs to keep running.

---

## Step 4: Access Admin Panel

### What this does:
Opens the admin panel login page in your web browser.

### How to do it:

**Open your web browser** (Chrome, Firefox, Edge, etc.)

**Navigate to:**
```
http://localhost:8000/admin/login
```

**What you'll see:**
- A login page with:
  - "🚀 Sokoni Africa" header
  - "Admin Panel Login" subtitle
  - Username/Email input field
  - Password input field
  - Login button

**Enter credentials:**
- **Username or Email**: `admin`
- **Password**: `admin123`

**Click "Login"**

**✅ Success:** You'll be redirected to the dashboard at `/admin`

**❌ If login fails:**
- Check that you created the admin user (Step 2)
- Verify the username/email matches what you created
- Make sure the password is correct
- Check the server terminal for error messages

---

## Step 5: Explore the Admin Panel

### Dashboard (`/admin`)
- View statistics: Total users, products, orders, revenue
- See recent activity (last 7 days)
- Quick action cards to navigate

### Users (`/admin/users`)
- See all registered users
- Search for specific users
- Filter by user type
- Activate/deactivate users
- Delete users

### Products (`/admin/products`)
- See all products
- Search products
- Filter by category
- Activate/deactivate products
- Delete products

### Orders (`/admin/orders`)
- See all orders
- Filter by status
- Update order status
- View order details

---

## 🔧 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'jinja2'"
**Solution:**
```bash
pip install jinja2 aiofiles
```

### Problem: "Could not connect to database"
**Solution:**
1. Check your `.env` file has `DATABASE_URL`
2. Make sure PostgreSQL is running
3. Verify database credentials are correct

### Problem: "Admin user already exists" but can't login
**Solution:**
1. Run `python create_admin_user.py` again
2. Type `y` to update the password
3. Try logging in again

### Problem: "404 Not Found" when accessing `/admin/login`
**Solution:**
1. Make sure server is running
2. Check you're accessing `http://localhost:8000/admin/login` (not `/api/admin/login`)
3. Verify `app/routers/admin.py` exists
4. Check server terminal for errors

### Problem: Static files (CSS/JS) not loading
**Solution:**
1. Verify `static/admin/css/style.css` exists
2. Check `main.py` has the static files mount
3. Restart the server

---

## 📝 Quick Reference

### Commands Summary

```bash
# 1. Navigate to backend
cd africa_sokoni_app_backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create admin user
python create_admin_user.py

# 4. Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. Open browser
# Go to: http://localhost:8000/admin/login
```

### Default Credentials
- **Username**: `admin`
- **Password**: `admin123`

### Important URLs
- **Login**: http://localhost:8000/admin/login
- **Dashboard**: http://localhost:8000/admin
- **Users**: http://localhost:8000/admin/users
- **Products**: http://localhost:8000/admin/products
- **Orders**: http://localhost:8000/admin/orders
- **API Docs**: http://localhost:8000/docs

---

## ✅ Verification Checklist

Before considering setup complete, verify:

- [ ] Dependencies installed (`pip install -r requirements.txt` completed)
- [ ] Admin user created (`python create_admin_user.py` ran successfully)
- [ ] Server starts without errors (`uvicorn main:app --reload`)
- [ ] Can access login page (http://localhost:8000/admin/login loads)
- [ ] Can login with admin credentials
- [ ] Dashboard displays statistics
- [ ] Can navigate to Users, Products, Orders pages
- [ ] CSS/styles are loading (page looks styled, not plain HTML)

---

## 🎯 Next Steps After Setup

1. **Change the default password** - Use the admin panel or update in database
2. **Explore features** - Try searching, filtering, managing users/products/orders
3. **Customize** - Edit templates or CSS to match your brand
4. **Deploy** - Follow `FREE_HOSTING_GUIDE.md` to deploy to free hosting

---

**Need help?** Check the full documentation in `ADMIN_PANEL_README.md`

