# Render Deployment Troubleshooting

## Problem: "Welcome to Render" Page Instead of API

If you see a "Welcome to Render" page when accessing your API, it means the service hasn't started correctly.

---

## ✅ Step 1: Check Deployment Status

1. Go to your Render Dashboard: https://dashboard.render.com
2. Click on your service: `sokoni-africa-app`
3. Check the **"Logs"** tab:
   - Look for errors in red
   - Check if the build completed
   - See if the service started

---

## 🔍 Common Issues & Fixes

### Issue 1: Root Directory Not Set

**Symptom**: Can't find `main.py`

**Fix**:
1. Go to **Settings** → **Build & Deploy**
2. Set **Root Directory** to: `africa_sokoni_app_backend`
3. Save changes (will redeploy)

---

### Issue 2: Wrong Start Command

**Symptom**: Service starts but crashes

**Fix**:
1. Go to **Settings** → **Build & Deploy**
2. Set **Start Command** to:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. Make sure **Root Directory** is set to `africa_sokoni_app_backend`

---

### Issue 3: Missing Environment Variables

**Symptom**: Service crashes on startup (check logs)

**Fix**:
1. Go to **Environment** tab
2. Make sure all variables from `RENDER_ENV_FINAL.txt` are added
3. Especially check:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `APP_BASE_URL`

---

### Issue 4: Build Failed

**Symptom**: Build errors in logs

**Common causes**:
- Missing `requirements.txt`
- Python version mismatch
- Dependencies can't install

**Fix**:
1. Check **Logs** tab for specific error
2. Verify `requirements.txt` exists in `africa_sokoni_app_backend/`
3. Check Python version in Render (should be 3.8+)

---

### Issue 5: Database Connection Failed

**Symptom**: Service starts but API returns 500 errors

**Fix**:
1. Verify `DATABASE_URL` is correct (Internal Database URL from Render PostgreSQL)
2. Check PostgreSQL service is running
3. Make sure database is accessible from your web service

---

## 🎯 Correct Configuration Checklist

In Render Dashboard, verify:

- [ ] **Name**: `sokoni-africa-app`
- [ ] **Root Directory**: `africa_sokoni_app_backend`
- [ ] **Runtime**: `Python 3`
- [ ] **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
- [ ] **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] **Plan**: Free or Paid
- [ ] **Environment Variables**: All added from `RENDER_ENV_FINAL.txt`

---

## 📋 Step-by-Step Fix

### 1. Check Logs First

Go to your service → **Logs** tab → Look for:
- ✅ "Application startup complete" = Good
- ❌ Red errors = Problem (copy the error message)

### 2. Verify Root Directory

**Settings** → **Build & Deploy**:
- **Root Directory**: `africa_sokoni_app_backend`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Check Environment Variables

**Environment** tab → Verify all variables are set:
- `DATABASE_URL`
- `SECRET_KEY`
- `APP_BASE_URL=https://sokoni-africa-app.onrender.com`
- All Flutterwave keys
- All email settings

### 4. Manual Deploy

If changes were made:
- Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## 🧪 Test After Fix

1. Wait for deployment to complete (green checkmark)
2. Try: `https://sokoni-africa-app.onrender.com/api/health`
3. Should see: `{"status": "healthy"}`
4. Try: `https://sokoni-africa-app.onrender.com/docs`
5. Should see: Swagger API documentation

---

## 🆘 Still Not Working?

### Check These:

1. **Service Status**: Should be "Live" (green)
2. **Last Deploy**: Should show success (green checkmark)
3. **Logs**: Copy any error messages
4. **Build Logs**: Check if build completed successfully

### Common Error Messages:

**"Module not found"**:
- Missing dependency in `requirements.txt`
- Add it and redeploy

**"Can't connect to database"**:
- Wrong `DATABASE_URL`
- Use Internal Database URL from Render PostgreSQL

**"Port already in use"**:
- Don't hardcode port, use `$PORT` environment variable

**"main.py not found"**:
- Root Directory is wrong
- Set to `africa_sokoni_app_backend`

---

## 📞 Need More Help?

1. Copy the exact error from **Logs** tab
2. Check **Build Logs** for build errors
3. Verify all configuration matches this guide

