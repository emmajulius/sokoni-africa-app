# Fix Render Settings

## Current Issues Found

### ✅ Correct:
- **Root Directory**: `africa_sokoni_app_backend` ✓

### ❌ Needs Fix:
- **Build Command**: Has invalid format `africa_sokoni_app_backend/$ pip install -r requirements.txt`
- **Start Command**: Need to verify this

---

## ✅ Correct Settings

### Build Command:
```
pip install --upgrade pip && pip install -r requirements.txt
```

**OR** (simpler version):
```
pip install -r requirements.txt
```

### Start Command:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 🔧 How to Fix

1. Go to your service: `sokoni-africa-app`
2. Click **"Settings"** tab
3. Scroll to **"Build & Deploy"** section
4. Update:

   **Build Command:**
   - Remove: `africa_sokoni_app_backend/$ pip install -r requirements.txt`
   - Replace with: `pip install --upgrade pip && pip install -r requirements.txt`

   **Start Command:**
   - Should be: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - If it's different, change it to this

5. Click **"Save Changes"** (bottom of page)
6. Render will automatically redeploy

---

## 📋 Complete Settings Checklist

In **Settings** → **Build & Deploy**:

- [ ] **Root Directory**: `africa_sokoni_app_backend`
- [ ] **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
- [ ] **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] **Runtime**: Python 3 (or specific version like 3.11)

---

## ⚠️ Important

After fixing:
1. **Save Changes**
2. Wait for **automatic redeploy** (you'll see "Deploying..." status)
3. Check **Logs** tab after deployment completes
4. Test: `https://sokoni-africa-app.onrender.com/api/health`

---

## 🎯 Next Steps

1. Fix the Build Command (remove `africa_sokoni_app_backend/$`)
2. Verify Start Command is correct
3. Save changes
4. Wait for redeploy
5. Check logs
6. Test the API

