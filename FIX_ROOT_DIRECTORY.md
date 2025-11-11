# Fix Root Directory Error

## Problem

```
Service Root Directory "/opt/render/project/src/africa_sokoni_app_backend" is missing.
builder.sh: line 51: cd: /opt/render/project/src/africa_sokoni_app_backend: No such file or directory
```

## Root Cause

The Root Directory is set to `africa_sokoni_app_backend`, but when we pushed to GitHub, we initialized git **inside** the `africa_sokoni_app_backend` folder. This means:

- **Repository root** = `africa_sokoni_app_backend` folder contents
- **Files are at root level** (main.py, requirements.txt, etc.)
- **NOT in a subfolder**

So Render is looking for `africa_sokoni_app_backend/africa_sokoni_app_backend/` which doesn't exist!

---

## ✅ Solution

### Change Root Directory to Empty

1. Go to Render Dashboard → Your Service → **Settings**
2. Scroll to **"Build & Deploy"**
3. Find **"Root Directory"**
4. **Clear it** (make it empty) or set it to `.` (dot)
5. **Save Changes**
6. Render will automatically redeploy

---

## Why This Happens

When we ran:
```powershell
cd africa_sokoni_app_backend
git init
git add .
git commit
```

We created a repository **inside** the backend folder, so:
- Repository root = backend files
- No subfolder needed

---

## ✅ Correct Settings After Fix

- **Root Directory**: (empty) or `.`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## 🎯 Steps to Fix

1. **Settings** → **Build & Deploy**
2. **Root Directory**: Delete `africa_sokoni_app_backend` (make it empty)
3. **Save Changes**
4. Wait for automatic redeploy
5. Check **Build Logs** - should work now!
6. Check **Logs** - should see startup messages
7. Test: `https://sokoni-africa-app.onrender.com/api/health`

---

## Expected Result

After fixing:
- Build should succeed
- Service should start
- Logs should appear
- API should work

