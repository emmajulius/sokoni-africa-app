# HOW TO GET YOUR OTP CODE

## In Development Mode (Current Setup):

When you request OTP from the app, the OTP code is **NOT sent to your phone**.
Instead, it's printed to the **backend console/terminal**.

### Steps to Get Your OTP:

1. **Open the terminal/console where your backend server is running**
   - This is where you ran: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

2. **Look for output like this:**
   ```
   ========================================================================
   🔐 DEVELOPMENT MODE - OTP NOT SENT VIA SMS
   ========================================================================
   📱 Phone Number: +255756556768
   🔑 OTP Code: 123456
   ⏰ Valid for: 10 minutes
   ========================================================================
   ⚠️  To receive real SMS, add Twilio credentials to .env file
   ========================================================================
   ```

3. **Copy the OTP Code** (the 6-digit number) and use it in your app

---

## To Get Real SMS on Your Phone:

You need to set up Twilio SMS service. Here's how:

### Step 1: Get Twilio Account
1. Go to https://www.twilio.com/
2. Sign up for a free account (includes free credits)
3. Get your credentials from the dashboard:
   - Account SID
   - Auth Token
   - Phone Number (they provide you one)

### Step 2: Add to .env File
Edit `sokoni_africa_app\africa_sokoni_app_backend\.env` and add:
```
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+1234567890
```

### Step 3: Restart Backend
Restart your backend server after adding Twilio credentials.

### Step 4: Test Again
Request OTP again - it should now be sent to your phone via SMS!

---

## Quick Summary:

**Right Now (Development Mode):**
- ✅ OTP is generated successfully
- ✅ Check backend console for the code
- ❌ NOT sent to phone (by design for testing)

**With Twilio Setup:**
- ✅ OTP is generated
- ✅ OTP is sent via SMS to your phone
- ✅ You receive it as a text message

