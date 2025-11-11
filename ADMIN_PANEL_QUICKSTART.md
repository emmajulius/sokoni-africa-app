# Admin Panel Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies

```bash
cd africa_sokoni_app_backend
pip install -r requirements.txt
```

This installs `jinja2` and `aiofiles` needed for the admin panel.

### Step 2: Create Admin User

```bash
python create_admin_user.py
```

This creates an admin user with:
- **Username**: `admin`
- **Email**: `admin@sokoniafrica.com`
- **Password**: `admin123`

⚠️ **Change the password after first login!**

### Step 3: Start Server & Access

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open: **http://localhost:8000/admin/login**

## 📋 Default Login Credentials

- **Username**: `admin`
- **Password**: `admin123`

## 🎯 What You Can Do

1. **Dashboard** (`/admin`) - View statistics and overview
2. **Users** (`/admin/users`) - Manage all users
3. **Products** (`/admin/products`) - Manage all products
4. **Orders** (`/admin/orders`) - Manage all orders

## 🔒 Change Admin Password

### Option 1: Environment Variables

Create/update `.env` file:
```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
ADMIN_EMAIL=admin@sokoniafrica.com
```

### Option 2: Update User in Database

Use the admin panel to update the admin user's password, or update directly in database.

## 🌐 Deploy to Free Hosting

The admin panel is ready for deployment! See `FREE_HOSTING_GUIDE.md` for details.

**Recommended**: Render.com (easiest free hosting)

## 📚 Full Documentation

See `ADMIN_PANEL_README.md` for complete documentation.

---

**That's it! Your admin panel is ready to use! 🎉**

