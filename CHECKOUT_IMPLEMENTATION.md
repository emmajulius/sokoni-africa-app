# Complete Checkout Implementation with Sokocoin

## Overview
This document describes the complete real-time checkout implementation using Sokocoin as the in-app currency, with automatic currency conversion between buyers and sellers.

## Architecture

### Currency Flow
1. **Products** are priced in seller's local currency (default: TZS)
2. **Buyer** sees prices converted to Sokocoin in real-time
3. **Payment** is processed entirely in Sokocoin
4. **Seller** receives payment in Sokocoin (converted from their local currency)
5. **Wallet transactions** are created for both buyer (PURCHASE) and seller (EARN)

### Exchange Rates
- **TZS**: 1 SOK = 1000 TZS
- **KES**: 1 SOK = 0.05 KES  
- **NGN**: 1 SOK = 0.5 NGN

These rates are configurable in `config.py`:
```python
SOKOCOIN_EXCHANGE_RATE_TZS: float = 1000.0
SOKOCOIN_EXCHANGE_RATE_KES: float = 52.6
SOKOCOIN_EXCHANGE_RATE_NGN: float = 585.0
```

## Backend Implementation

### Order Creation Endpoint
**POST** `/api/orders`

**Process Flow:**
1. Validates cart is not empty
2. Calculates total in local currency (seller's currency)
3. Converts to Sokocoin using exchange rates
4. Checks buyer's Sokocoin balance
5. Deducts Sokocoin from buyer's wallet
6. Credits seller's wallet with converted Sokocoin
7. Creates wallet transactions for both parties
8. Creates order and order items
9. Clears cart
10. Sends notifications to buyer and seller

**Key Features:**
- Real-time balance checking
- Automatic currency conversion
- Atomic transaction (all or nothing)
- Wallet balance updates immediately
- Transaction history for both parties

### Wallet Transactions Created

**Buyer Transaction:**
- Type: `PURCHASE`
- Status: `COMPLETED`
- Amount: Total Sokocoin deducted
- Description: "Purchase - Order #{order_id}"

**Seller Transaction:**
- Type: `EARN`
- Status: `COMPLETED`
- Amount: Seller's portion in Sokocoin
- Description: "Sale - Order #{order_id} from {buyer_username}"

## Frontend Implementation

### Checkout Screen (`checkout_screen.dart`)

**Features:**
- Displays real-time Sokocoin wallet balance
- Shows required Sokocoin amount for order
- Warns if insufficient balance
- Shows currency conversion (local + Sokocoin)
- Fetches shipping address from user profile
- Validates address selection before proceeding

**Key Calculations:**
```dart
// Exchange rate is defined as: 1 Sokocoin = X local currency
// So to convert local currency to Sokocoin: local_amount / exchange_rate
_subtotalSokocoin = subtotal_local / exchange_rate
_shippingSokocoin = shipping_local / exchange_rate
_totalSokocoin = _subtotalSokocoin + _shippingSokocoin
```

### Payment Screen (`payment_screen.dart`)

**Features:**
- Final order summary with Sokocoin amounts
- Real-time balance verification before payment
- Creates order via API (triggers Sokocoin deduction)
- Shows success/error messages
- Navigates to main screen on success

**Payment Process:**
1. Verifies wallet balance one more time
2. Calls `OrderService.createOrder()`
3. Backend processes payment atomically
4. Shows success message with order ID
5. Navigates away from checkout flow

### Order Service (`order_service.dart`)

**Methods:**
- `getOrders()` - Fetch user's orders
- `createOrder()` - Create new order with Sokocoin payment
- `getOrder()` - Get specific order details
- `getSales()` - Get seller's sales (orders for their products)

## Real-Time Features

### 1. Balance Checking
- Checkout screen shows current balance
- Payment screen verifies balance before processing
- Backend validates balance before deducting

### 2. Currency Conversion
- Products priced in seller's currency
- Automatically converted to Sokocoin for display
- Conversion happens in real-time on frontend
- Backend uses same rates for consistency

### 3. Wallet Updates
- Buyer's balance deducted immediately
- Seller's balance credited immediately
- Both transactions marked as COMPLETED
- No pending states for purchases

### 4. Transaction History
- Buyer sees PURCHASE transaction
- Seller sees EARN transaction
- Both show order ID in description
- Full transaction details available

## Data Flow

```
Cart Items (Local Currency)
    ↓
Checkout Screen (Convert to Sokocoin)
    ↓
Payment Screen (Verify Balance)
    ↓
Order Creation API
    ↓
Backend Processing:
  - Convert to Sokocoin
  - Check balance
  - Deduct from buyer
  - Credit seller
  - Create transactions
  - Create order
  - Clear cart
    ↓
Success Response
    ↓
Navigate to Main Screen
```

## Error Handling

### Insufficient Balance
- Frontend: Shows warning in checkout screen
- Frontend: Disables "Place Order" button
- Backend: Returns 400 error with balance details
- Frontend: Shows error dialog with details

### Network Errors
- Frontend: Shows error dialog
- Backend: Transaction rolled back (no deduction)
- User can retry payment

### Validation Errors
- Empty cart: Backend returns 400
- Invalid address: Frontend prevents submission
- Missing products: Backend skips invalid items

## Security Features

1. **Authentication Required**: All endpoints require valid JWT token
2. **User Verification**: Backend verifies user owns wallet
3. **Balance Validation**: Multiple checks prevent overdraft
4. **Atomic Transactions**: All-or-nothing processing
5. **Transaction Logging**: All wallet changes are logged

## Testing Checklist

- [ ] Add items to cart
- [ ] Navigate to checkout
- [ ] Verify Sokocoin balance display
- [ ] Verify currency conversion
- [ ] Test with insufficient balance
- [ ] Test with sufficient balance
- [ ] Complete purchase
- [ ] Verify buyer's balance deducted
- [ ] Verify seller's balance credited
- [ ] Check transaction history
- [ ] Verify order created
- [ ] Verify cart cleared

## Future Enhancements

1. **Multi-Currency Support**: Detect seller's currency from location
2. **Multi-Seller Orders**: Split orders by seller
3. **Shipping Cost Calculation**: Dynamic shipping based on location
4. **Tax Calculation**: Add tax support
5. **Discount Codes**: Apply discounts before conversion
6. **Order Splitting**: Handle orders with items from multiple sellers

## Configuration

### Backend (.env)
```env
SOKOCOIN_EXCHANGE_RATE_TZS=1000.0
SOKOCOIN_EXCHANGE_RATE_KES=52.6
SOKOCOIN_EXCHANGE_RATE_NGN=585.0
```

### Frontend (constants.dart)
Exchange rates should match backend for consistency.

## API Endpoints Used

- `GET /api/wallet/balance` - Get wallet balance
- `GET /api/cart` - Get cart items
- `POST /api/orders` - Create order (with Sokocoin payment)
- `GET /api/users/me` - Get user profile (for shipping address)

## Notes

- All amounts are stored in local currency in the order table
- Sokocoin amounts are calculated on-the-fly for display
- Wallet balances are always in Sokocoin
- Exchange rates are configurable per currency
- Default currency is TZS (can be enhanced to detect from user location)

