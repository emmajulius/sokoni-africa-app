# Cashout Feature Improvements

## Summary
This document outlines all the improvements made to the cashout feature to fix issues with balance deduction, error handling, and user experience.

## Key Changes

### 1. Fixed Balance Deduction Issue
**Problem**: Sokocoin balance was being deducted immediately when initiating cashout, even if the transfer failed. This left users with reduced balance for failed transactions.

**Solution**: 
- Balance is now only deducted **after** Flutterwave confirms the transfer was successful
- Failed transactions no longer affect the wallet balance
- Transaction status is properly tracked throughout the process

**Files Modified**:
- `app/routers/wallet.py` - Changed cashout flow to deduct balance only on success

### 2. Improved Phone Number Validation
**Problem**: Users could enter phone numbers in local format (e.g., `0712...`) which caused confusion.

**Solution**:
- Now **requires** international format with country code (e.g., `+2557XXXXXXXX`)
- Clear validation error messages
- UI hints guide users to enter correct format

**Files Modified**:
- `app/routers/wallet.py` - Updated `_normalize_mobile_money_number()` function
- `lib/screens/wallet/cashout_screen.dart` - Added validation and hints

### 3. Enhanced Error Handling
**Problem**: Generic error messages didn't help users understand what went wrong.

**Solution**:
- Specific error messages for different failure scenarios:
  - IP Whitelisting errors
  - Timeout errors
  - Authentication errors
  - Validation errors
- User-friendly error dialogs in the Flutter app
- Better error parsing from Flutterwave API responses

**Files Modified**:
- `app/routers/wallet.py` - Enhanced exception handling
- `flutterwave_service.py` - Improved error detection and messages
- `lib/screens/wallet/cashout_screen.dart` - Better error display

### 4. Sandbox/Test Mode Support
**Problem**: IP whitelisting requirement blocked testing in development.

**Solution**:
- Added `MOCK_CASHOUT_TRANSFERS` configuration option
- Automatically uses mock mode when test keys are detected
- Allows testing without IP whitelisting

**Configuration**:
Add to `.env` file:
```
MOCK_CASHOUT_TRANSFERS=true  # For sandbox testing
```

**Files Modified**:
- `config.py` - Added `MOCK_CASHOUT_TRANSFERS` setting
- `app/routers/wallet.py` - Added mock transfer logic

### 5. Stuck Transaction Cleanup
**Problem**: If a transaction got stuck in PENDING status, users couldn't recover their balance.

**Solution**:
- New endpoint to clean up stuck transactions
- Automatically refunds Sokocoin for transactions stuck > 1 hour
- Can be called manually by users

**API Endpoint**:
```
POST /api/wallet/cashout/cleanup-stuck
```

**Files Added/Modified**:
- `app/routers/wallet.py` - Added cleanup endpoint
- `lib/services/wallet_service.dart` - Added cleanup method

## Usage Instructions

### For Development/Testing

1. **Enable Mock Mode** (Optional):
   Add to `.env`:
   ```
   MOCK_CASHOUT_TRANSFERS=true
   ```

2. **Or Use Test Keys**:
   Use Flutterwave test keys (starting with `FLWSECK_TEST-`)

### For Production

1. **Whitelist Server IP**:
   - Get your backend server's public IP address
   - Add it to Flutterwave Dashboard → Settings → API → IP Whitelist

2. **Use Live Keys**:
   - Use Flutterwave live keys (starting with `FLWSECK-`)
   - Ensure `MOCK_CASHOUT_TRANSFERS=false` or not set

### Phone Number Format

**Required Format**: International format with country code
- Tanzania: `+2557XXXXXXXX` (e.g., `+255712345678`)
- Kenya: `+2547XXXXXXXX` (e.g., `+254712345678`)
- Nigeria: `+234XXXXXXXXXX` (e.g., `+2348123456789`)

**Invalid Formats** (will be rejected):
- `0712345678` (missing country code)
- `255712345678` (missing + prefix)
- `712345678` (missing country code)

### Cleaning Up Stuck Transactions

If you notice your balance is incorrect due to failed cashouts:

1. **Via API**:
   ```dart
   final walletService = WalletService();
   final result = await walletService.cleanupStuckCashouts();
   print(result['message']); // Shows how many transactions were refunded
   ```

2. **Automatically**:
   Transactions older than 1 hour in PENDING status are automatically considered stuck

## Error Messages

### IP Whitelisting Error
```
Flutterwave rejected the transfer because the server IP is not whitelisted.
Add your backend server's public IP address to the IP whitelist in the Flutterwave dashboard
or set MOCK_CASHOUT_TRANSFERS=true in the backend .env for sandbox testing.
```

### Phone Number Validation Error
```
Provide the phone number in international format, e.g. +2557XXXXXXXX
```

### Timeout Error
```
The transfer request timed out. Please check your internet connection and try again.
```

## Testing Checklist

- [ ] Cashout with valid international phone number succeeds
- [ ] Cashout with invalid phone format shows proper error
- [ ] Failed cashout doesn't deduct balance
- [ ] Successful cashout deducts correct amount
- [ ] Stuck transaction cleanup works
- [ ] Error messages are user-friendly
- [ ] Mock mode works for testing

## Migration Notes

If you have existing stuck transactions from before this update:

1. Call the cleanup endpoint to refund stuck transactions
2. Check wallet balance matches expected amount
3. Verify transaction history shows correct statuses

## Support

If you encounter issues:
1. Check Flutterwave dashboard for API errors
2. Verify IP whitelisting is configured (for live mode)
3. Check backend logs for detailed error messages
4. Use cleanup endpoint to recover stuck transactions

