# How to Get Email Credentials for Render

## 📧 What You Need

You need **Gmail App Password** credentials to send emails from your backend. Here's how to get them:

---

## 🔑 Step-by-Step Guide

### Step 1: Use Your Gmail Account

You'll need a Gmail account. If you don't have one, create one at https://gmail.com

**Current email in config:** `emmajulius2512@gmail.com`

---

### Step 2: Enable 2-Step Verification

Gmail requires 2-Step Verification to generate App Passwords.

1. Go to https://myaccount.google.com/security
2. Scroll to **"2-Step Verification"**
3. Click **"Get Started"** or **"Turn On"**
4. Follow the prompts to set it up (usually via phone number)

---

### Step 3: Generate App Password

Once 2-Step Verification is enabled:

1. Go to https://myaccount.google.com/apppasswords
   - Or: Google Account → Security → 2-Step Verification → App Passwords
2. You may need to sign in again
3. Under **"Select app"**, choose **"Mail"**
4. Under **"Select device"**, choose **"Other (Custom name)"**
5. Type: **"Sokoni Africa Backend"** (or any name you like)
6. Click **"Generate"**
7. **Copy the 16-character password** (it looks like: `abcd efgh ijkl mnop`)
   - Remove spaces when using it: `abcdefghijklmnop`

---

### Step 4: Use the Credentials

Now you have everything you need:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USERNAME=your-email@gmail.com          # Your Gmail address
EMAIL_PASSWORD=abcdefghijklmnop            # The 16-char app password (no spaces)
EMAIL_FROM=your-email@gmail.com             # Same as EMAIL_USERNAME
EMAIL_FROM_NAME=Sokoni Africa               # Display name in emails
```

---

## 📋 Example (Based on Current Config)

If you're using `emmajulius2512@gmail.com`:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USERNAME=emmajulius2512@gmail.com
EMAIL_PASSWORD=wyehxgjynsrvkphl              # This is your current app password
EMAIL_FROM=emmajulius2512@gmail.com
EMAIL_FROM_NAME=Research Gears              # Or "Sokoni Africa"
```

---

## ⚠️ Important Notes

1. **App Password ≠ Regular Password**
   - You CANNOT use your regular Gmail password
   - You MUST generate an App Password after enabling 2-Step Verification

2. **Keep It Secret**
   - App passwords are like API keys - keep them secure
   - Don't share them or commit them to public repositories

3. **If You Lose It**
   - Just generate a new one at https://myaccount.google.com/apppasswords
   - Update it in Render's environment variables

4. **Multiple Apps**
   - You can generate multiple app passwords for different services
   - Each one is independent and can be revoked separately

---

## 🧪 Test Your Credentials

After adding to Render, test by:
1. Using the "Forgot Password" feature in your app
2. Enter an email address
3. Check if the email arrives (check spam folder too)

---

## 🔄 Alternative: Use a Different Email Provider

If you don't want to use Gmail, you can use other providers:

### Outlook/Hotmail
```
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USERNAME=your-email@outlook.com
EMAIL_PASSWORD=your-app-password
```

### Custom SMTP Server
```
EMAIL_HOST=your-smtp-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USERNAME=your-username
EMAIL_PASSWORD=your-password
```

---

## ✅ Quick Checklist

- [ ] Have a Gmail account
- [ ] Enable 2-Step Verification
- [ ] Generate App Password
- [ ] Copy the 16-character password (remove spaces)
- [ ] Add all 6 email variables to Render
- [ ] Test by sending a password reset email

---

## 🆘 Troubleshooting

**"Invalid credentials" error:**
- Make sure you're using App Password, not regular password
- Check that 2-Step Verification is enabled
- Verify no extra spaces in the password

**"Connection refused" error:**
- Check EMAIL_HOST is correct (`smtp.gmail.com`)
- Check EMAIL_PORT is `587`
- Check EMAIL_USE_TLS is `True`

**Emails not arriving:**
- Check spam/junk folder
- Verify recipient email is correct
- Check Render logs for error messages

