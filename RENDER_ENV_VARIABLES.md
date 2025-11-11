# Environment Variables for Render Deployment

## ✅ **YES - Add These to Render** (Required)

Copy these from your local `.env` file to Render's Environment Variables:

### Database
```
DATABASE_URL=<Use Render's Internal Database URL from PostgreSQL service>
```
**Important**: Use the **Internal Database URL** from your Render PostgreSQL service, not your local one.

### Security
```
SECRET_KEY=<Your existing SECRET_KEY from .env>
ALGORITHM=HS256
```
**Note**: If you don't have a `SECRET_KEY`, generate a new one:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### App Configuration
```
APP_BASE_URL=https://your-service-name.onrender.com
DEBUG=False
ENVIRONMENT=production
```
**Important**: Replace `your-service-name` with your actual Render service name.

### Flutterwave (Payment Gateway)
```
FLW_SECRET_KEY=<Your Flutterwave Secret Key>
FLW_PUBLIC_KEY=<Your Flutterwave Public Key>
FLW_ENCRYPTION_KEY=<Your Flutterwave Encryption Key>
FLUTTERWAVE_BASE_URL=https://api.flutterwave.com/v3
MOCK_CASHOUT_TRANSFERS=False
MOCK_FLUTTERWAVE_TOPUPS=False
```

### Email Configuration
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USERNAME=<Your email>
EMAIL_PASSWORD=<Your email app password>
EMAIL_FROM=<Your email>
EMAIL_FROM_NAME=Research Gears
```

### CORS (Important for Mobile App)
```
ALLOWED_ORIGINS=*
```
This allows your mobile app to connect. You can restrict this later if needed.

### Exchange Rates (Optional - defaults are in config.py)
```
# Reference: 1 SOK = 1000 TZS
# 1 TZS = 0.0527 KES => 1 SOK = 52.7 KES
# 1 TZS = 0.587 NGN => 1 SOK = 587 NGN
SOKOCOIN_EXCHANGE_RATE_TZS=1000.0
SOKOCOIN_EXCHANGE_RATE_KES=52.7
SOKOCOIN_EXCHANGE_RATE_NGN=587.0
```

### Platform Fees (Optional - defaults are in config.py)
```
PROCESSING_FEE_RATE=0.02
SHIPPING_BASE_FEE_SOK=2.0
SHIPPING_RATE_PER_KM_SOK=0.5
SHIPPING_MIN_DISTANCE_KM=1.0
```

---

## ⚠️ **CHANGE These Values** (Don't copy as-is)

### 1. `DATABASE_URL`
- **Local**: `postgresql://user:pass@localhost:5432/sokoni_db`
- **Render**: Use the **Internal Database URL** from your Render PostgreSQL dashboard
- Format: `postgresql://user:pass@dpg-xxxxx-a.oregon-postgres.render.com:5432/dbname`

### 2. `APP_BASE_URL`
- **Local**: `http://localhost:8000`
- **Render**: `https://your-service-name.onrender.com`
- **Critical**: This is used for generating callback URLs, email links, etc.

### 3. `DEBUG`
- **Local**: `True`
- **Render**: `False` (for security)

### 4. `ENVIRONMENT`
- **Local**: `development`
- **Render**: `production`

---

## ❌ **DON'T Copy These** (Local-only or Not Needed)

- `ACCESS_TOKEN_EXPIRE_MINUTES` - Has a default (30), but you can set it if you want
- `ALLOWED_ORIGIN_REGEX` - Not needed if `ALLOWED_ORIGINS=*`
- Any local file paths
- Any localhost URLs

---

## 📋 **Quick Checklist**

When adding variables to Render:

1. ✅ Copy `SECRET_KEY`, `ALGORITHM`
2. ✅ Copy all `FLW_*` keys
3. ✅ Copy all `EMAIL_*` settings
4. ✅ Copy exchange rates (or leave defaults)
5. ✅ Copy platform fees (or leave defaults)
6. ⚠️ **CHANGE** `DATABASE_URL` to Render's Internal URL
7. ⚠️ **CHANGE** `APP_BASE_URL` to your Render service URL
8. ⚠️ **CHANGE** `DEBUG=False` and `ENVIRONMENT=production`
9. ✅ Set `ALLOWED_ORIGINS=*` (or specific origins)

---

## 🔒 **Security Best Practices**

1. **Never commit `.env` to Git** - It should be in `.gitignore`
2. **Use Render's Environment Variables** - They're encrypted and secure
3. **Rotate secrets periodically** - Especially `SECRET_KEY` and API keys
4. **Use different keys for production** - Don't use the same Flutterwave keys for dev and prod if possible

---

## 🚀 **How to Add Variables in Render**

1. Go to your Web Service dashboard
2. Click on **Environment** tab
3. Click **Add Environment Variable**
4. Enter **Key** and **Value**
5. Click **Save Changes**
6. Render will automatically redeploy with new variables

---

## 📝 **Example Complete .env for Render**

```env
# Database (from Render PostgreSQL service)
DATABASE_URL=postgresql://user:pass@dpg-xxxxx-a.oregon-postgres.render.com:5432/dbname

# Security
SECRET_KEY=your-generated-secret-key-here
ALGORITHM=HS256

# App
APP_BASE_URL=https://sokoni-africa-backend.onrender.com
DEBUG=False
ENVIRONMENT=production

# CORS
ALLOWED_ORIGINS=*

# Flutterwave
FLW_SECRET_KEY=FLWSECK_TEST-xxxxx
FLW_PUBLIC_KEY=FLWPUBK_TEST-xxxxx
FLW_ENCRYPTION_KEY=xxxxx
FLUTTERWAVE_BASE_URL=https://api.flutterwave.com/v3
MOCK_CASHOUT_TRANSFERS=False
MOCK_FLUTTERWAVE_TOPUPS=False

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Research Gears

# Exchange Rates (optional - defaults in config.py)
# Reference: 1 SOK = 1000 TZS
# 1 TZS = 0.0527 KES => 1 SOK = 52.7 KES
# 1 TZS = 0.587 NGN => 1 SOK = 587 NGN
SOKOCOIN_EXCHANGE_RATE_TZS=1000.0
SOKOCOIN_EXCHANGE_RATE_KES=52.7
SOKOCOIN_EXCHANGE_RATE_NGN=587.0

# Platform Fees (optional - defaults in config.py)
PROCESSING_FEE_RATE=0.02
SHIPPING_BASE_FEE_SOK=2.0
SHIPPING_RATE_PER_KM_SOK=0.5
SHIPPING_MIN_DISTANCE_KM=1.0
```

---

## ✅ **After Adding Variables**

1. **Save** all environment variables in Render
2. **Wait for redeploy** (automatic)
3. **Check logs** to ensure app starts correctly
4. **Test** the admin panel and API endpoints

