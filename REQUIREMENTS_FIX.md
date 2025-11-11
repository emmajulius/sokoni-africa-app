# Critical: Set Python Version in Render Settings

## ⚠️ IMPORTANT: You MUST Set Python Version in Render

The `runtime.txt` file is NOT being recognized. You **MUST** set it manually in Render settings.

---

## ✅ Step-by-Step Fix (DO THIS NOW)

### 1. Go to Render Dashboard
- https://dashboard.render.com
- Click your service: `sokoni-africa-app`

### 2. Open Settings
- Click **"Settings"** tab
- Scroll to **"Build & Deploy"** section

### 3. Find "Runtime" or "Python Version"
- Look for a dropdown that says "Runtime" or "Python Version"
- It might be near the top of Build & Deploy section

### 4. Select Python 3.11
- Click the dropdown
- Select: **Python 3.11** (or Python 3.12)
- **NOT** Python 3.13

### 5. Update Build Command
- Find **"Build Command"**
- Change it to:
  ```
  pip install --upgrade pip && pip install --only-binary :all: -r requirements.txt || pip install --prefer-binary -r requirements.txt
  ```

### 6. Save Changes
- Click **"Save Changes"** button (usually at bottom)
- Render will automatically redeploy

---

## 🎯 Why This is Critical

- **Python 3.13** = Too new, packages try to build from source (needs Rust)
- **Python 3.11/3.12** = Have pre-built wheels (no compilation needed)
- **--only-binary** = Forces use of wheels only (no source builds)

---

## 📋 After Saving

1. **Wait for redeploy** (you'll see "Deploying..." status)
2. **Check Build Logs** - should show Python 3.11
3. **Packages install from wheels** (fast, no Rust errors)
4. **Build succeeds!**

---

## 🆘 If You Don't See "Runtime" Option

Some Render interfaces show it differently:
- Look for **"Environment"** → **"PYTHON_VERSION"** variable
- Or **"Advanced"** settings
- Or contact Render support

---

## ✅ Verification

After setting Python 3.11, check Build Logs:
- Should see: `Python 3.11.x` (not 3.13)
- Should see: `Installing collected packages` (no Rust/Cargo errors)
- Should see: `Successfully installed...`

---

## ⚠️ This is the ONLY way to fix it

The `runtime.txt` file is not working. You MUST set Python version in Render settings manually.

