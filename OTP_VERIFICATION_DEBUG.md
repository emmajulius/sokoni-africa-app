# OTP Verification Troubleshooting

## Common Issues and Solutions:

### Issue 1: "Invalid OTP code"
**Possible causes:**
- Phone number format mismatch (e.g., +255756556768 vs 255756556768)
- OTP code already used
- Wrong OTP code entered
- OTP expired (valid for 10 minutes)

**Solution:**
1. Check backend console for detailed error messages
2. Make sure phone number format matches exactly (with + prefix)
3. Request a new OTP if expired or used

### Issue 2: Verification succeeds but doesn't login
**Possible causes:**
- User doesn't exist (new user registration flow)
- Response handling issue in Flutter app

**Solution:**
- Check backend console - it will show if user exists or not
- If user doesn't exist, you need to complete registration first

### Issue 3: Phone number format mismatch
**Check:**
- When sending OTP: Phone format used (e.g., +255756556768)
- When verifying: Phone format must match EXACTLY

**Fix:**
- Ensure phone number format is consistent in both requests

## Debugging Steps:

1. **Check Backend Console** when you verify OTP:
   - Look for: `🔍 VERIFYING OTP`
   - It will show: Phone number and code being verified
   - It will show: Recent OTPs if verification fails

2. **Check Flutter Console** for:
   - `🔐 Verifying OTP...`
   - `📱 Phone: ...`
   - `🔑 Code: ...`
   - Response status and body

3. **Most Common Issue:**
   - Request new OTP
   - Use the LATEST OTP code from backend console
   - Make sure phone number matches exactly

## Quick Test:

1. Request new OTP
2. Check backend console for the code
3. Copy the code exactly (including spaces if any)
4. Verify immediately (within 10 minutes)
5. Check both backend and Flutter console for errors

