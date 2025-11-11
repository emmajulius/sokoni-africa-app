# OTP Troubleshooting Guide

## Quick Fix Steps:

### Step 1: Make sure backend is running
```powershell
cd sokoni_africa_app\africa_sokoni_app_backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Important:** Use `--host 0.0.0.0` so mobile devices can connect!

### Step 2: Update IP Address in Flutter App
1. Find your computer's IP address:
   - Windows: Run `ipconfig` and look for IPv4 Address (usually 192.168.x.x)
   - The IP we found: `192.168.1.186`
   
2. Update `sokoni_africa_app/lib/utils/constants.dart`:
   ```dart
   static const String baseUrl = 'http://192.168.1.186:8000';
   ```

### Step 3: Test Backend Directly
Run the test script:
```powershell
python sokoni_africa_app\africa_sokoni_app_backend\test_otp.py
```

### Step 4: Check OTP in Backend Console
When you request OTP from the app:
- In development mode (without Twilio), OTP is printed to the backend console
- Look for output like:
  ```
  ============================================================
  DEVELOPMENT MODE: OTP for +255123456789
  OTP Code: 123456
  ============================================================
  ```

### Step 5: Common Issues

**Issue: "Connection refused" or "Request timeout"**
- ✅ Backend not running → Start it with `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- ✅ Wrong IP address → Update constants.dart with correct IP
- ✅ Firewall blocking → Allow port 8000 in Windows Firewall

**Issue: "OTP not received"**
- ✅ Check backend console - OTP is printed there in dev mode
- ✅ For real SMS, add Twilio credentials to .env file

**Issue: Mobile app can't connect**
- ✅ Use your computer's IP (192.168.1.186) not localhost
- ✅ Make sure phone and computer are on same WiFi network
- ✅ For Android emulator, use: `http://10.0.2.2:8000`

### Step 6: Enable Real SMS (Optional)
Add to `.env` file:
```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

### Testing Checklist:
- [ ] Backend running on port 8000
- [ ] Backend accessible at http://192.168.1.186:8000/docs
- [ ] Flutter app constants.dart updated with correct IP
- [ ] Phone and computer on same WiFi network
- [ ] Check backend console for OTP codes

