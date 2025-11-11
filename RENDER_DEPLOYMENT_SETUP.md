# Render Deployment Setup Guide

## Problem: "Repository is Empty"

Render needs your code to be in a **Git repository** (GitHub, GitLab, or Bitbucket) before it can deploy.

---

## ✅ Solution: Push Your Code to GitHub

### Step 1: Create a GitHub Repository

1. Go to **https://github.com** and sign in
2. Click the **"+"** icon → **"New repository"**
3. Fill in:
   - **Repository name**: `sokoni-africa-backend` (or any name you like)
   - **Description**: "Sokoni Africa Backend API"
   - **Visibility**: Choose **Private** (recommended) or **Public**
   - **DO NOT** check "Initialize with README" (we already have files)
4. Click **"Create repository"**

---

### Step 2: Initialize Git in Your Backend Folder

Open PowerShell/Terminal in your backend folder and run:

```powershell
# Navigate to backend folder
cd C:\Users\DELL\Desktop\Sokoni_Africa_App\sokoni_africa_app\africa_sokoni_app_backend

# Initialize git repository
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit: Sokoni Africa Backend"
```

---

### Step 3: Connect to GitHub and Push

After creating the GitHub repository, GitHub will show you commands. Use these:

```powershell
# Add GitHub repository as remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/sokoni-africa-backend.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Note**: You'll need to authenticate with GitHub. You can:
- Use GitHub Desktop (easier)
- Use Personal Access Token (PAT)
- Use GitHub CLI

---

### Step 4: Connect Repository to Render

1. Go to **Render Dashboard** → **New +** → **Web Service**
2. Click **"Connect GitHub"** (or GitLab/Bitbucket)
3. Authorize Render to access your repositories
4. Select your repository: `sokoni-africa-backend`
5. Render will now detect your code!

---

## 🚀 Alternative: Use GitHub Desktop (Easier)

If command line is confusing, use **GitHub Desktop**:

### Step 1: Download GitHub Desktop
- Go to: https://desktop.github.com
- Download and install

### Step 2: Add Repository
1. Open GitHub Desktop
2. Click **"File"** → **"Add Local Repository"**
3. Browse to: `C:\Users\DELL\Desktop\Sokoni_Africa_App\sokoni_africa_app\africa_sokoni_app_backend`
4. Click **"Add Repository"**

### Step 3: Publish to GitHub
1. In GitHub Desktop, click **"Publish repository"**
2. Choose:
   - **Name**: `sokoni-africa-backend`
   - **Keep this code private** (recommended)
3. Click **"Publish Repository"**
4. Done! Your code is now on GitHub

### Step 4: Connect to Render
- Go to Render → New Web Service → Connect GitHub → Select your repo

---

## 📋 Quick Checklist

- [ ] Created GitHub account (if you don't have one)
- [ ] Created new GitHub repository
- [ ] Initialized git in backend folder (`git init`)
- [ ] Added all files (`git add .`)
- [ ] Made first commit (`git commit -m "Initial commit"`)
- [ ] Connected to GitHub (`git remote add origin ...`)
- [ ] Pushed to GitHub (`git push -u origin main`)
- [ ] Connected repository to Render
- [ ] Render can now see your code!

---

## ⚠️ Important Notes

### Files NOT to Commit

Make sure `.env` is in `.gitignore` (it already is). Never commit:
- `.env` file (contains secrets)
- `__pycache__/` folders
- `*.pyc` files
- Database files

### If You Get "Authentication Failed"

When pushing to GitHub, you might need a **Personal Access Token**:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click **"Generate new token"**
3. Give it a name: "Render Deployment"
4. Select scopes: **repo** (full control)
5. Click **"Generate token"**
6. **Copy the token** (you won't see it again!)
7. When Git asks for password, paste the token instead

---

## 🎯 After Pushing to GitHub

Once your code is on GitHub:

1. **Go to Render** → **New +** → **Web Service**
2. **Connect GitHub** → Select your repository
3. **Configure**:
   - **Name**: `sokoni-africa-app`
   - **Root Directory**: `africa_sokoni_app_backend`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Add Environment Variables** (from `RENDER_ENV_FINAL.txt`)
5. **Deploy!**

---

## 🆘 Troubleshooting

**"Repository is empty" error:**
- Make sure you pushed code to GitHub
- Check that you selected the correct repository in Render
- Verify the branch name (usually `main` or `master`)

**"Authentication failed" when pushing:**
- Use Personal Access Token instead of password
- Or use GitHub Desktop (easier)

**"Can't find main.py" error:**
- Set **Root Directory** to `africa_sokoni_app_backend` in Render settings

---

## 📞 Need Help?

- GitHub Docs: https://docs.github.com
- Render Docs: https://render.com/docs
- Git Tutorial: https://git-scm.com/docs

