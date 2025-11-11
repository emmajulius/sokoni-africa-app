# CRITICAL: Fix Python 3.13 Issue

## ⚠️ The Problem

Render is using **Python 3.13** which tries to build packages from source (needs Rust/Cargo). This fails because the file system is read-only.

**Error shows**: `/opt/render/project/src/.venv/bin/python3.13`

---

## ✅ Solution: Set Python Version via Environment Variable

Since the UI setting might not be visible, use an environment variable:

### Step 1: Go to Environment Variables

1. Render Dashboard → Your Service → **"Environment"** tab
2. Click **"Add Environment Variable"**

### Step 2: Add Python Version Variable

- **Key**: `PYTHON_VERSION`
- **Value**: `3.11.9`
- Click **"Save Changes"**

### Step 3: Also Try This Variable

Add another one:
- **Key**: `RUNTIME_VERSION`
- **Value**: `python-3.11.9`
- Click **"Save Changes"**

---

## ✅ Alternative: Check Build Settings

1. Go to **Settings** → **Build & Deploy**
2. Look for ANY of these:
   - "Runtime"
   - "Python Version"
   - "Python Runtime"
   - "Runtime Version"
   - "Buildpack" (might have Python version option)

3. If you see ANY dropdown related to Python, select **3.11**

---

## ✅ Update Build Command

While you're there, update Build Command:

**Current**: `pip install -r requirements.txt`

**Change to**:
```
pip install --upgrade pip && pip install --only-binary :all: -r requirements.txt || pip install --prefer-binary -r requirements.txt
```

This forces binary wheels and avoids source builds.

---

## 🆘 If Still Not Working

### Option 1: Delete and Recreate Service

1. **Settings** → Scroll to bottom → **"Danger Zone"**
2. **Delete Service**
3. Create new service
4. **During creation**, look for Python version option
5. Select **Python 3.11** before creating

### Option 2: Contact Render Support

If you can't find Python version setting anywhere:
- Go to Render Dashboard
- Click **"Help"** or **"Support"**
- Ask: "How do I set Python version to 3.11 for my web service?"

---

## 📋 What to Check

After adding environment variables:

1. **Save all changes**
2. **Wait for redeploy**
3. **Check Build Logs** - should show Python 3.11
4. **Look for**: `Python 3.11.x` (not 3.13)

---

## 🎯 Most Important

The error MUST show Python 3.11 in Build Logs, not 3.13. If it still shows 3.13, the Python version is not being set correctly.

---

## Quick Test

After setting environment variables, check Build Logs for:
- ✅ `Python 3.11.x` = Good!
- ❌ `Python 3.13.x` = Still wrong, try other methods

