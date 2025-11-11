# How to Get Flutterwave API Keys

## 🔑 What You Need

You need **3 keys** from Flutterwave:
1. **Secret Key** (`FLW_SECRET_KEY`)
2. **Public Key** (`FLW_PUBLIC_KEY`)
3. **Encryption Key** (`FLW_ENCRYPTION_KEY`)

---

## 📋 Step-by-Step Guide

### Step 1: Log in to Flutterwave Dashboard

1. Go to: **https://dashboard.flutterwave.com**
2. Sign in with your Flutterwave account
   - If you don't have an account, sign up at https://flutterwave.com

---

### Step 2: Navigate to API Keys Section

1. Once logged in, look for **"Settings"** in the sidebar menu
2. Click on **"Settings"** → **"API Keys"**
   - Or look for **"API Keys"** directly in the menu

---

### Step 3: Get Your Keys

You'll see different sections:

#### A. **Test Keys** (For Development/Testing)
- Use these when testing your app
- Keys start with:
  - Secret Key: `FLWSECK_TEST-...`
  - Public Key: `FLWPUBK_TEST-...`

#### B. **Live Keys** (For Production)
- Use these when your app is live
- Keys start with:
  - Secret Key: `FLWSECK-...` (no TEST)
  - Public Key: `FLWPUBK-...` (no TEST)

---

### Step 4: Copy Each Key

1. **Secret Key** (`FLW_SECRET_KEY`):
   - Click the **"Copy"** or **"Reveal"** button next to "Secret Key"
   - Format: `FLWSECK_TEST-xxxxxxxxxxxxxxxxxxxxx` (test) or `FLWSECK-xxxxxxxxxxxxxxxxxxxxx` (live)

2. **Public Key** (`FLW_PUBLIC_KEY`):
   - Click the **"Copy"** or **"Reveal"** button next to "Public Key"
   - Format: `FLWPUBK_TEST-xxxxxxxxxxxxxxxxxxxxx` (test) or `FLWPUBK-xxxxxxxxxxxxxxxxxxxxx` (live)

3. **Encryption Key** (`FLW_ENCRYPTION_KEY`):
   - Look for **"Encryption Key"** or **"Encryption"** section
   - Click **"Copy"** or **"Reveal"**
   - Format: Usually a long string of characters (no prefix)

---

## 📝 Example Format

Your keys will look like this:

```
FLW_SECRET_KEY=FLWSECK_TEST-1234567890abcdefghijklmnopqrstuvwxyz123456
FLW_PUBLIC_KEY=FLWPUBK_TEST-1234567890abcdefghijklmnopqrstuvwxyz123456
FLW_ENCRYPTION_KEY=1234567890abcdef1234567890abcdef
```

---

## ⚠️ Important Notes

### Test vs Live Keys

- **For Development/Testing**: Use **Test Keys** (contain `TEST` in the name)
- **For Production**: Use **Live Keys** (no `TEST` in the name)

### Security

- **Never commit keys to Git** - They should be in `.env` file (which is in `.gitignore`)
- **Keep keys secret** - Don't share them publicly
- **Rotate keys** if compromised - You can regenerate them in the dashboard

### IP Whitelisting (For Production)

When using **Live Keys**, you may need to:
1. Go to **Settings** → **API** → **IP Whitelist**
2. Add your Render server's IP address
3. This prevents unauthorized access

---

## 🎯 For Render Deployment

Add these to Render's Environment Variables:

```
FLW_SECRET_KEY=FLWSECK_TEST-xxxxxxxxxxxxxxxxxxxxx
FLW_PUBLIC_KEY=FLWPUBK_TEST-xxxxxxxxxxxxxxxxxxxxx
FLW_ENCRYPTION_KEY=xxxxxxxxxxxxxxxxxxxxx
FLUTTERWAVE_BASE_URL=https://api.flutterwave.com/v3
MOCK_CASHOUT_TRANSFERS=False
MOCK_FLUTTERWAVE_TOPUPS=False
```

**Note**: 
- Use **Test Keys** first to test everything works
- Switch to **Live Keys** when ready for production

---

## 🔍 Where to Find in Dashboard

If you can't find the keys:

1. **Check the sidebar menu**:
   - Settings → API Keys
   - Or: Developer → API Keys
   - Or: Account → API Keys

2. **Look for tabs**:
   - "Test API Keys" tab
   - "Live API Keys" tab

3. **Alternative locations**:
   - Settings → Developer → API Keys
   - Account Settings → API Keys
   - Developer Tools → API Keys

---

## ✅ Quick Checklist

- [ ] Logged into Flutterwave Dashboard
- [ ] Navigated to Settings → API Keys
- [ ] Copied Secret Key (`FLWSECK_TEST-...` or `FLWSECK-...`)
- [ ] Copied Public Key (`FLWPUBK_TEST-...` or `FLWPUBK-...`)
- [ ] Copied Encryption Key
- [ ] Added all 3 keys to Render environment variables
- [ ] Set `FLUTTERWAVE_BASE_URL=https://api.flutterwave.com/v3`
- [ ] Set `MOCK_CASHOUT_TRANSFERS=False` and `MOCK_FLUTTERWAVE_TOPUPS=False`

---

## 🆘 Troubleshooting

**"I can't find the Encryption Key":**
- Some accounts may not show it immediately
- Check if there's a "Show Encryption Key" button
- Contact Flutterwave support if missing

**"Invalid authorization key" error:**
- Make sure you're using **Secret Key**, not Client Secret
- Check for extra spaces when copying
- Verify you're using the correct key type (Test vs Live)

**"API authentication failed":**
- Double-check all 3 keys are correct
- Ensure no extra spaces or line breaks
- Verify you're using keys from the correct environment (Test/Live)

---

## 📞 Need Help?

- Flutterwave Support: https://support.flutterwave.com
- Flutterwave Documentation: https://developer.flutterwave.com/docs

