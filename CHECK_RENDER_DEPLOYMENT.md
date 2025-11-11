# Check Render Deployment Status

## Problem: "Welcome to Agnoga" Black Screen

This means your FastAPI service is NOT running correctly on Render.

---

## 🔍 Step 1: Check Render Logs

1. Go to: https://dashboard.render.com
2. Click your service: `sokoni-africa-app`
3. Click **"Logs"** tab
4. Look for:
   - ✅ "Application startup complete" = Good
   - ❌ Red errors = Problem
   - ⚠️ "Module not found" = Missing dependency
   - ⚠️ "Can't find main.py" = Wrong root directory

**Copy any error messages you see!**

---

## ✅ Step 2: Verify Service Configuration

Go to **Settings** → **Build & Deploy**:

### Must Have:
- **Root Directory**: `africa_sokoni_app_backend`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`

### Check Runtime:
- **Runtime**: Python 3 (or Python 3.11, 3.10, etc.)

---

## 🧪 Step 3: Test the Correct Endpoints

After fixing, try these URLs:

1. **Root endpoint**:
   ```
   https://sokoni-africa-app.onrender.com/
   ```
   Should return: `{"message": "Welcome to Sokoni Africa API", "version": "1.0.0", "docs": "/docs"}`

2. **Health check**:
   ```
   https://sokoni-africa-app.onrender.com/api/health
   ```
   Should return: `{"status": "healthy"}`

3. **API Docs**:
   ```
   https://sokoni-africa-app.onrender.com/docs
   ```
   Should show: Swagger UI documentation

---

## 🔧 Common Fixes

### Fix 1: Root Directory Not Set

**Problem**: Render can't find `main.py`

**Solution**:
1. Settings → Build & Deploy
2. Set **Root Directory**: `africa_sokoni_app_backend`
3. Save (auto-redeploys)

---

### Fix 2: Wrong Start Command

**Problem**: Service doesn't start

**Solution**:
1. Settings → Build & Deploy
2. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Save

---

### Fix 3: Missing Dependencies

**Problem**: "Module not found" errors

**Solution**:
1. Check `requirements.txt` exists in `africa_sokoni_app_backend/`
2. Check logs for which module is missing
3. Add it to `requirements.txt`
4. Push to GitHub
5. Render will auto-redeploy

---

### Fix 4: Database Connection Error

**Problem**: Service starts but crashes on database access

**Solution**:
1. Check `DATABASE_URL` in Environment Variables
2. Use **Internal Database URL** from Render PostgreSQL
3. Format: `postgresql://user:pass@host:5432/dbname`

---

## 📋 Quick Checklist

Before asking for help, check:

- [ ] Service status is "Live" (green) in Render
- [ ] Root Directory = `africa_sokoni_app_backend`
- [ ] Start Command = `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] All environment variables are set
- [ ] Logs show "Application startup complete"
- [ ] No red errors in logs
- [ ] Build completed successfully (green checkmark)

---

## 🆘 Still Seeing "Welcome to Agnoga"?

This suggests:
1. **Wrong service URL** - Check you're accessing the correct Render service
2. **Service not deployed** - Check if service is actually running
3. **Cached page** - Try hard refresh (Ctrl+F5) or incognito mode
4. **Different service** - Make sure you're looking at the right service in Render dashboard

---

## 📞 What to Share for Help

If still not working, share:
1. **Screenshot of Logs tab** (showing errors)
2. **Service Settings** (Root Directory, Start Command)
3. **Environment Variables** (names only, not values)
4. **Build status** (success/failed)

