# Admin Panel - Sokoni Africa

A complete, production-ready admin panel built with FastAPI and Jinja2 templates for managing the Sokoni Africa e-commerce platform.

## 🚀 Features

- **Dashboard**: Overview with key statistics (users, products, orders, revenue)
- **User Management**: View, search, activate/deactivate, and delete users
- **Product Management**: View, search, filter by category, activate/deactivate, and delete products
- **Order Management**: View all orders, filter by status, update order status
- **Modern UI**: Clean, responsive design with beautiful styling
- **Authentication**: Secure admin login with session management
- **Search & Filter**: Advanced search and filtering capabilities
- **Pagination**: Efficient pagination for large datasets

## 📁 Project Structure

```
africa_sokoni_app_backend/
├── app/
│   └── routers/
│       └── admin.py          # Admin routes and logic
├── templates/
│   └── admin/
│       ├── base.html         # Base template
│       ├── login.html        # Login page
│       ├── dashboard.html    # Dashboard
│       ├── users.html        # Users management
│       ├── products.html     # Products management
│       └── orders.html       # Orders management
├── static/
│   └── admin/
│       ├── css/
│       │   └── style.css     # Admin panel styles
│       └── js/
│           └── main.js       # Admin panel JavaScript
└── main.py                   # FastAPI app (includes admin routes)
```

## 🛠️ Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The admin panel requires:
- `jinja2==3.1.2` - Template engine
- `aiofiles==23.2.1` - Async file operations

### 2. Create Admin User

You need to create an admin user in your database. The admin panel checks for:
- Username matching `ADMIN_USERNAME` (default: "admin")
- OR Email matching `ADMIN_EMAIL` (default: "admin@sokoniafrica.com")

**Option 1: Use existing user**
- Update a user's username or email to match admin credentials
- Set a password for that user

**Option 2: Create new admin user**
Run this Python script:

```python
from database import SessionLocal
from models import User, UserType
from auth import get_password_hash

db = SessionLocal()

# Create admin user
admin_user = User(
    username="admin",
    email="admin@sokoniafrica.com",
    full_name="Admin User",
    hashed_password=get_password_hash("admin123"),  # Change this!
    user_type=UserType.CLIENT,  # Can be any type
    is_active=True,
    is_verified=True
)

db.add(admin_user)
db.commit()
print("Admin user created!")
```

### 3. Configure Admin Credentials (Optional)

Set environment variables to customize admin credentials:

```bash
# .env file
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
ADMIN_EMAIL=admin@sokoniafrica.com
```

**⚠️ IMPORTANT**: Change the default password in production!

### 4. Start the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access Admin Panel

Open your browser and navigate to:
- **Login**: http://localhost:8000/admin/login
- **Dashboard**: http://localhost:8000/admin (after login)

**Default Credentials**:
- Username: `admin`
- Password: `admin123`

## 📋 Admin Panel Routes

| Route | Description |
|-------|-------------|
| `/admin/login` | Admin login page |
| `/admin` | Dashboard (requires login) |
| `/admin/users` | Users management |
| `/admin/products` | Products management |
| `/admin/orders` | Orders management |
| `/admin/logout` | Logout |

## 🔐 Security

### Current Implementation
- Admin authentication via JWT tokens stored in cookies
- Admin check by username/email matching environment variables
- Session-based authentication (24-hour token expiry)

### Production Recommendations
1. **Change default password** immediately
2. **Use environment variables** for admin credentials
3. **Add `is_admin` field** to User model for better admin management
4. **Implement role-based access** (RBAC) for multiple admin levels
5. **Add IP whitelisting** for admin routes
6. **Enable HTTPS** for all admin routes
7. **Add rate limiting** to prevent brute force attacks
8. **Implement 2FA** for admin accounts

## 🎨 Customization

### Styling
Edit `static/admin/css/style.css` to customize the appearance.

### Templates
Edit files in `templates/admin/` to modify the UI structure.

### Adding New Features
1. Add routes in `app/routers/admin.py`
2. Create templates in `templates/admin/`
3. Update navigation in `templates/admin/base.html`

## 📊 Features Breakdown

### Dashboard
- Total users count
- Total products count
- Total orders count
- Total revenue (SOK)
- Recent activity (last 7 days)
- Quick action cards

### Users Management
- List all users with pagination
- Search by username, email, or full name
- Filter by user type (client, supplier, retailer)
- Activate/deactivate users
- Delete users (with confirmation)
- View user details

### Products Management
- List all products with pagination
- Search by title or description
- Filter by category
- View product images
- Activate/deactivate products
- Delete products (with confirmation)
- See product type (regular/auction)

### Orders Management
- List all orders with pagination
- Filter by order status
- View order details (customer, seller, items, total)
- Update order status (dropdown)
- See order creation date

## 🚢 Deployment

### For Free Hosting (Render.com, Railway, Fly.io)

The admin panel is ready for deployment! Just:

1. **Push to GitHub**
2. **Deploy to your hosting platform**
3. **Set environment variables**:
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD`
   - `ADMIN_EMAIL`
4. **Create admin user** in database
5. **Access**: `https://your-app.onrender.com/admin/login`

### Environment Variables for Production

```env
# Admin Panel
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here
ADMIN_EMAIL=admin@yourdomain.com

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Other settings...
```

## 📝 Notes

- The admin panel uses the same database as your main API
- All admin operations use your existing models and schemas
- No separate database or service needed
- Fully integrated with your FastAPI backend
- Works seamlessly with your existing authentication system

## 🐛 Troubleshooting

### Can't login?
1. Check if admin user exists in database
2. Verify username/email matches `ADMIN_USERNAME` or `ADMIN_EMAIL`
3. Ensure user has a password set
4. Check browser console for errors

### Static files not loading?
1. Verify `static/` directory exists
2. Check `main.py` mounts static files correctly
3. Ensure file paths are correct

### Templates not found?
1. Verify `templates/admin/` directory exists
2. Check Jinja2 is installed: `pip install jinja2`
3. Restart the server after installing dependencies

## 🎯 Next Steps

Consider adding:
- [ ] Analytics charts (using Chart.js)
- [ ] Export data to CSV/Excel
- [ ] Bulk operations (bulk delete, bulk activate)
- [ ] User activity logs
- [ ] System settings management
- [ ] Email notifications for admin actions
- [ ] Advanced filtering and sorting
- [ ] Product image upload in admin panel
- [ ] Order details modal/view page

## 📞 Support

For issues or questions, check:
- Main API documentation: `/docs`
- Backend README: `README.md`
- Free hosting guide: `FREE_HOSTING_GUIDE.md`

---

**Built with ❤️ for Sokoni Africa**

