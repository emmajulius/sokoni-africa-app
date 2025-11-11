# Fix GitHub Authentication Error

## Problem
```
remote: Permission to emmajulius/sokoni-africa-app.git denied to mahikimb.
fatal: unable to access 'https://github.com/emmajulius/sokoni-africa-app.git/': The requested URL returned error: 403
```

**Issue**: You're logged in as `mahikimb` but trying to push to `emmajulius`'s repository.

---

## ✅ Solution: Use Personal Access Token

### Step 1: Create Personal Access Token

1. Go to: **https://github.com/settings/tokens**
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Fill in:
   - **Note**: "Render Deployment" (or any name)
   - **Expiration**: Choose 90 days or No expiration
   - **Select scopes**: Check **`repo`** (full control of private repositories)
4. Click **"Generate token"**
5. **COPY THE TOKEN** (you won't see it again!)
   - It looks like: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

### Step 2: Update Remote URL with Token

Run this command (replace `YOUR_TOKEN` with the token you copied):

```powershell
git remote set-url origin https://YOUR_TOKEN@github.com/emmajulius/sokoni-africa-app.git
```

**Example**:
```powershell
git remote set-url origin https://ghp_abc123xyz@github.com/emmajulius/sokoni-africa-app.git
```

---

### Step 3: Push Again

```powershell
git push -u origin main
```

When prompted for password, just press Enter (the token in the URL handles authentication).

---

## 🔄 Alternative: Use GitHub Credential Manager

### Option 1: Update Windows Credential Manager

1. Open **Windows Credential Manager**:
   - Press `Win + R`
   - Type: `control /name Microsoft.CredentialManager`
   - Press Enter

2. Go to **"Windows Credentials"** tab
3. Find `git:https://github.com`
4. Click **"Edit"**
5. Update:
   - **User name**: `emmajulius`
   - **Password**: Your Personal Access Token (not your GitHub password)
6. Click **"Save"**

### Option 2: Clear and Re-authenticate

```powershell
# Clear cached credentials
git credential-manager-core erase
# Or on Windows:
git credential reject https://github.com

# Then push (it will ask for credentials)
git push -u origin main
# Username: emmajulius
# Password: YOUR_PERSONAL_ACCESS_TOKEN
```

---

## 🎯 Quick Fix (Easiest)

1. **Get Personal Access Token** from https://github.com/settings/tokens
2. **Update remote URL**:
   ```powershell
   git remote set-url origin https://YOUR_TOKEN@github.com/emmajulius/sokoni-africa-app.git
   ```
3. **Push**:
   ```powershell
   git push -u origin main
   ```

---

## ⚠️ Security Note

- **Never commit tokens to Git**
- **Never share tokens publicly**
- Tokens are like passwords - keep them secret
- You can revoke tokens anytime from GitHub settings

---

## 🆘 Still Not Working?

1. **Check repository ownership**: Make sure you have write access to `emmajulius/sokoni-africa-app`
2. **Verify token permissions**: Token must have `repo` scope
3. **Try SSH instead**: Set up SSH keys (more secure for long-term)

