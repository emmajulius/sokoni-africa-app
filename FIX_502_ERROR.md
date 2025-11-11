# Fix 502 Bad Gateway Error

## What 502 Means

502 Bad Gateway = Your service crashed or isn't responding. Common causes:

1. **Service crashed on startup** (check logs)
2. **Missing environment variables**
3. **Database connection failed**
4. **Service is sleeping** (free tier - first request after sleep)
5. **Application error**

---

## ✅ Step 1: Check Render Logs

1. Go to Render Dashboard → Your Service
2. Click **"Logs"** tab
3. Look for:
   - ❌ Red errors
   - ⚠️ "Application startup failed"
   - ⚠️ "Module not found"
   - ⚠️ "Database connection error"
   - ⚠️ "Environment variable missing"

**What errors do you see?** (Copy them here)

---

## ✅ Step 2: Check Service Status

1. Look at the top of your service page
2. What does it say?
   - **"Live"** = Service is running (but might have crashed)
   - **"Building"** = Still deploying
   - **"Failed"** = Build failed
   - **"Sleeping"** = Free tier - service is asleep

---

## ✅ Step 3: Common Fixes

### Fix 1: Service Sleeping (Free Tier)

**Symptom**: First request after inactivity takes 30+ seconds, might show 502

**Solution**: 
- Wait 30-60 seconds for service to wake up
- Try again
- Consider upgrading to paid plan for always-on

---

### Fix 2: Missing Environment Variables

**Symptom**: Logs show "Environment variable not set"

**Solution**:
1. Go to **Environment** tab
2. Verify all variables from `RENDER_ENV_FINAL.txt` are set:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `APP_BASE_URL`
   - All Flutterwave keys
   - All email settings

---

### Fix 3: Database Connection Error

**Symptom**: Logs show "Can't connect to database"

**Solution**:
1. Check `DATABASE_URL` in Environment variables
2. Use **Internal Database URL** (not external)
3. Format: `postgresql://user:pass@host:5432/dbname`
4. Verify PostgreSQL service is running

---

### Fix 4: Application Crash

**Symptom**: Logs show Python errors

**Common causes**:
- Missing dependency in `requirements.txt`
- Import error
- Syntax error in code

**Solution**:
1. Check Build Logs for errors
2. Check Runtime Logs for Python tracebacks
3. Fix the error
4. Push to GitHub (auto-redeploys)

---

### Fix 5: Port Binding Issue

**Symptom**: Service starts but crashes immediately

**Solution**:
1. Verify **Start Command** is:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
2. Make sure it uses `$PORT` (not hardcoded port)

---

## 🔍 Quick Diagnostic

Run these checks:

1. **Service Status**: Live / Building / Failed / Sleeping?
2. **Logs Tab**: Any red errors?
3. **Build Logs**: Did build succeed?
4. **Environment Variables**: All set?
5. **Database**: PostgreSQL service running?

---

## 🆘 Most Common: Service Sleeping

If you're on free tier:
- Service sleeps after 15 minutes of inactivity
- First request wakes it up (takes 30-60 seconds)
- You might see 502 during wake-up
- **Solution**: Wait and try again, or upgrade to paid plan

---

## 📋 What to Check Now

1. **Open Render Dashboard** → Your Service
2. **Check Logs tab** - What errors do you see?
3. **Check service status** - What does it say?
4. **Share the error messages** from logs

---

## 🎯 Quick Fixes to Try

1. **Manual Deploy**: Settings → Manual Deploy → Deploy latest commit
2. **Check Environment Variables**: Make sure all are set
3. **Wait if sleeping**: Free tier services need time to wake up
4. **Check Database**: PostgreSQL service must be running

---

## What to Share

Please tell me:
1. **What do you see in Logs tab?** (any errors?)
2. **Service status?** (Live, Building, Failed, Sleeping?)
3. **Any error messages?** (copy from logs)

This will help me identify the exact issue!

