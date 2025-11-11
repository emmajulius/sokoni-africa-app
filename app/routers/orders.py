import math
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_, or_, case
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from database import get_db
from models import Order, OrderItem, CartItem, Product, User, OrderStatus, Notification, Wallet, WalletTransaction, WalletTransactionType, WalletTransactionStatus
from schemas import OrderCreate, OrderResponse, OrderItemResponse
from auth import get_current_user, get_current_active_user, require_user_type
from models import UserType
from config import settings
from collections import defaultdict

router = APIRouter()


def _get_or_create_wallet(user_id: int, db: Session) -> Wallet:
    """Get or create a wallet for a user"""
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def _get_exchange_rate(currency: str) -> float:
    """Get exchange rate for converting local currency to Sokocoin"""
    currency_upper = currency.upper()
    if currency_upper == "TZS":
        return settings.SOKOCOIN_EXCHANGE_RATE_TZS
    elif currency_upper == "KES":
        return settings.SOKOCOIN_EXCHANGE_RATE_KES
    elif currency_upper == "NGN":
        return settings.SOKOCOIN_EXCHANGE_RATE_NGN
    else:
        # Default to 1:1 for unknown currencies
        return 1.0


def _convert_to_sokocoin(local_amount: float, currency: str = "TZS") -> float:
    """Convert local currency amount to Sokocoin
    Exchange rate is defined as: 1 Sokocoin = X local currency
    So to convert local currency to Sokocoin: local_amount / exchange_rate
    """
    exchange_rate = _get_exchange_rate(currency)
    if exchange_rate <= 0:
        return 0.0
    return local_amount / exchange_rate


def _convert_from_sokocoin(sok_amount: float, currency: str = "TZS") -> float:
    """Convert Sokocoin amount to local currency"""
    exchange_rate = _get_exchange_rate(currency)
    return sok_amount * exchange_rate


def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """Calculate distance between two coordinates using Haversine formula (kilometers)."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    R = 6371.0  # Earth radius km
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return round(distance, 2)


def _calculate_shipping_fee(distance_km: float) -> float:
    """
    Calculate shipping fee based on distance.
    - If distance is 0km or None: No shipping fee (same location, pickup available)
    - If distance is very small (< 0.1km = 100m): No shipping fee (essentially same location)
    - Otherwise: Base fee + (distance * per_km rate), with minimum distance applied
    """
    # Handle None or invalid distance
    if distance_km is None:
        return 0.0
    
    # If distance is effectively 0 (same location or very close < 100m), no shipping fee
    # This allows for pickup or very local delivery
    if distance_km < 0.1:
        return 0.0
    
    base_fee = max(settings.SHIPPING_BASE_FEE_SOK, 0.0)
    per_km = max(settings.SHIPPING_RATE_PER_KM_SOK, 0.0)
    min_distance = max(settings.SHIPPING_MIN_DISTANCE_KM, 0.0)

    # Apply minimum distance threshold for distances >= 0.1km
    # This ensures consistent pricing for short distances
    effective_distance = max(distance_km, min_distance)
    fee = base_fee + (effective_distance * per_km)
    return round(fee, 2)


@router.get("", response_model=List[OrderResponse])
async def get_orders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's orders"""
    orders = (
        db.query(Order)
        .filter(Order.customer_id == current_user.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc())
        .all()
    )
    
    responses: List[OrderResponse] = []
    for order in orders:
        order_response = _build_order_response(order, db)
        if order_response:
            responses.append(order_response)
    return responses


@router.get("/sales", response_model=List[OrderResponse])
async def get_sales(
    current_user: User = Depends(require_user_type(UserType.SUPPLIER, UserType.RETAILER)),
    db: Session = Depends(get_db)
):
    """Get orders for current user's products (sellers only)"""
    orders = (
        db.query(Order)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Product, OrderItem.product_id == Product.id)
        .filter(Product.seller_id == current_user.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc())
        .all()
    )
    
    responses: List[OrderResponse] = []
    seen_order_ids = set()
    for order in orders:
        if order.id in seen_order_ids:
            continue
        order_response = _build_order_response(order, db, seller_id=current_user.id)
        if order_response and order_response.items:
            responses.append(order_response)
            seen_order_ids.add(order.id)
    return responses


@router.get("/analytics")
async def get_sales_analytics(
    period: Optional[str] = Query("all", description="Time period: daily, weekly, monthly, yearly, all"),
    current_user: User = Depends(require_user_type(UserType.SUPPLIER, UserType.RETAILER)),
    db: Session = Depends(get_db)
):
    """Get comprehensive sales analytics for the current seller"""
    # Calculate date range based on period
    now = datetime.now(timezone.utc)
    start_date = None
    
    if period == "daily":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        start_date = now - timedelta(days=7)
    elif period == "monthly":
        start_date = now - timedelta(days=30)
    elif period == "yearly":
        start_date = now - timedelta(days=365)
    # "all" means no date filter
    
    # Base query for seller's orders
    base_query = (
        db.query(Order)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Product, OrderItem.product_id == Product.id)
        .filter(Product.seller_id == current_user.id)
    )
    
    if start_date:
        base_query = base_query.filter(Order.created_at >= start_date)
    
    # Get all orders for this seller
    orders = base_query.options(selectinload(Order.items).selectinload(OrderItem.product)).all()
    
    # Remove duplicate orders
    seen_order_ids = set()
    unique_orders = []
    for order in orders:
        if order.id not in seen_order_ids:
            unique_orders.append(order)
            seen_order_ids.add(order.id)
    
    # Calculate metrics
    total_revenue = 0.0
    total_orders = len(unique_orders)
    total_products_sold = 0
    order_status_count = defaultdict(int)
    product_sales = defaultdict(lambda: {"quantity": 0, "revenue": 0.0, "name": ""})
    daily_revenue = defaultdict(float)
    monthly_revenue = defaultdict(float)
    customer_count = set()
    
    for order in unique_orders:
        # Calculate revenue for this seller's items only
        order_revenue = 0.0
        order_quantity = 0
        
        for item in order.items:
            product = item.product
            if product and product.seller_id == current_user.id:
                item_revenue = (item.price or 0.0) * (item.quantity or 1)
                order_revenue += item_revenue
                order_quantity += item.quantity or 1
                
                # Track product sales
                product_sales[product.id]["quantity"] += item.quantity or 1
                product_sales[product.id]["revenue"] += item_revenue
                product_sales[product.id]["name"] = product.title
        
        total_revenue += order_revenue
        total_products_sold += order_quantity
        
        # Track order status
        order_status_count[order.status.value] += 1
        
        # Track customers
        customer_count.add(order.customer_id)
        
        # Track revenue by day
        order_date = order.created_at.date()
        daily_revenue[order_date.isoformat()] += order_revenue
        
        # Track revenue by month
        month_key = order.created_at.strftime("%Y-%m")
        monthly_revenue[month_key] += order_revenue
    
    # Calculate average order value
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
    
    # Get top products
    top_products = sorted(
        [
            {
                "product_id": product_id,
                "name": data["name"],
                "quantity_sold": data["quantity"],
                "revenue": data["revenue"]
            }
            for product_id, data in product_sales.items()
        ],
        key=lambda x: x["revenue"],
        reverse=True
    )[:10]
    
    # Prepare time series data
    time_series = []
    if period in ["daily", "weekly"]:
        # Daily data for last 7-30 days
        days_to_show = 7 if period == "weekly" else 30
        for i in range(days_to_show):
            date = (now - timedelta(days=i)).date()
            date_str = date.isoformat()
            time_series.append({
                "date": date_str,
                "revenue": daily_revenue.get(date_str, 0.0),
                "orders": sum(1 for o in unique_orders if o.created_at.date() == date)
            })
        time_series.reverse()
    elif period == "monthly":
        # Monthly data for last 12 months
        for i in range(12):
            date = now - timedelta(days=30 * i)
            month_key = date.strftime("%Y-%m")
            time_series.append({
                "month": month_key,
                "revenue": monthly_revenue.get(month_key, 0.0),
                "orders": sum(1 for o in unique_orders if o.created_at.strftime("%Y-%m") == month_key)
            })
        time_series.reverse()
    elif period == "yearly":
        # Yearly data
        years = {}
        for order in unique_orders:
            year = order.created_at.year
            if year not in years:
                years[year] = {"revenue": 0.0, "orders": 0}
            order_revenue = sum((item.price or 0.0) * (item.quantity or 1) for item in order.items if item.product and item.product.seller_id == current_user.id)
            years[year]["revenue"] += order_revenue
            years[year]["orders"] += 1
        
        for year in sorted(years.keys()):
            time_series.append({
                "year": year,
                "revenue": years[year]["revenue"],
                "orders": years[year]["orders"]
            })
    else:  # all time
        # Group by month for all time
        for month_key in sorted(monthly_revenue.keys()):
            time_series.append({
                "month": month_key,
                "revenue": monthly_revenue[month_key],
                "orders": sum(1 for o in unique_orders if o.created_at.strftime("%Y-%m") == month_key)
            })
    
    # Calculate growth metrics (compare with previous period)
    previous_period_revenue = 0.0
    if period == "daily":
        prev_start = now - timedelta(days=1)
        prev_end = now
    elif period == "weekly":
        prev_start = now - timedelta(days=14)
        prev_end = now - timedelta(days=7)
    elif period == "monthly":
        prev_start = now - timedelta(days=60)
        prev_end = now - timedelta(days=30)
    elif period == "yearly":
        # Previous year
        prev_start = now - timedelta(days=730)
        prev_end = now - timedelta(days=365)
    else:
        prev_start = None
        prev_end = None
    
    if prev_start and prev_end:
        prev_orders = (
            db.query(Order)
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(
                Product.seller_id == current_user.id,
                Order.created_at >= prev_start,
                Order.created_at < prev_end
            )
            .all()
        )
        
        seen_prev_order_ids = set()
        for order in prev_orders:
            if order.id in seen_prev_order_ids:
                continue
            seen_prev_order_ids.add(order.id)
            for item in order.items:
                if item.product and item.product.seller_id == current_user.id:
                    previous_period_revenue += (item.price or 0.0) * (item.quantity or 1)
    
    revenue_growth = 0.0
    if previous_period_revenue > 0:
        revenue_growth = ((total_revenue - previous_period_revenue) / previous_period_revenue) * 100
    elif total_revenue > 0:
        revenue_growth = 100.0
    
    return {
        "period": period,
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "average_order_value": round(avg_order_value, 2),
            "total_products_sold": total_products_sold,
            "unique_customers": len(customer_count),
            "revenue_growth": round(revenue_growth, 2),
        },
        "order_status_breakdown": dict(order_status_count),
        "top_products": top_products,
        "time_series": time_series,
        "date_range": {
            "start": start_date.isoformat() if start_date else None,
            "end": now.isoformat()
        }
    }


@router.get("/shipping/estimate")
async def estimate_shipping(
    seller_id: int = Query(..., description="Seller ID to calculate distance against"),
    current_user: User = Depends(require_user_type(UserType.CLIENT, UserType.RETAILER)),
    db: Session = Depends(get_db)
):
    """Estimate shipping distance and fee between buyer and seller."""
    buyer = db.query(User).filter(User.id == current_user.id).first()
    seller = db.query(User).filter(User.id == seller_id).first()

    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller not found"
        )

    if buyer.latitude is None or buyer.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set your address with location details first."
        )

    if seller.latitude is None or seller.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller has not provided a pickup location yet."
        )

    distance_km = _calculate_distance(buyer.latitude, buyer.longitude, seller.latitude, seller.longitude)
    if distance_km is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to calculate distance for shipping."
        )

    shipping_fee = _calculate_shipping_fee(distance_km)

    return {
        "distance_km": distance_km,
        "shipping_fee_sok": shipping_fee,
        "currency": "SOK",
        "base_fee": settings.SHIPPING_BASE_FEE_SOK,
        "rate_per_km": settings.SHIPPING_RATE_PER_KM_SOK,
    }


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get order by ID"""
    order = (
        db.query(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user has access to this order
    is_customer = order.customer_id == current_user.id
    is_seller = order.seller_id == current_user.id
    if not is_customer and not is_seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this order"
        )
    
    order_response = _build_order_response(order, db, seller_id=current_user.id if is_seller else None)
    if not order_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare order response"
        )
    return order_response


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(require_user_type(UserType.CLIENT, UserType.RETAILER)),
    db: Session = Depends(get_db)
):
    """Create order from cart items with Sokocoin payment"""
    # Get user's cart items
    cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    
    # Get buyer and seller wallets
    buyer_wallet = _get_or_create_wallet(current_user.id, db)
    
    # Calculate totals and convert to Sokocoin
    # Products are priced in Sokocoin internally (local price stored separately for reference)
    total_local_amount = 0.0
    total_sokocoin = 0.0
    order_items_data = []
    seller_amounts = {}  # Track amounts per seller for wallet credits
    default_currency = None
    
    for cart_item in cart_items:
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()
        if not product:
            continue
        
        seller_id = product.seller_id
        item_currency = (product.local_currency or default_currency or "TZS").upper()
        if default_currency is None:
            default_currency = item_currency
        
        local_unit_price = product.local_price
        if local_unit_price is None:
            base_sok_price = product.price or 0.0
            local_unit_price = _convert_from_sokocoin(base_sok_price, item_currency)
        sok_unit_price = product.price or _convert_to_sokocoin(local_unit_price, item_currency)
        
        item_local_total = local_unit_price * cart_item.quantity
        item_sokocoin = sok_unit_price * cart_item.quantity
        
        total_local_amount += item_local_total
        total_sokocoin += item_sokocoin
        
        # Track seller amounts
        if seller_id not in seller_amounts:
            seller_amounts[seller_id] = {"local": 0.0, "sokocoin": 0.0, "currency": item_currency}
        seller_amounts[seller_id]["local"] += item_local_total
        seller_amounts[seller_id]["sokocoin"] += item_sokocoin
        
        order_items_data.append({
            "product_id": product.id,
            "quantity": cart_item.quantity,
            "price": sok_unit_price,
            "seller_id": seller_id,
            "sokocoin_amount": item_sokocoin,
            "currency": item_currency
        })
    
    if not order_items_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid products in cart"
        )
    
    processing_fee_rate = max(settings.PROCESSING_FEE_RATE or 0.0, 0.0)
    processing_fee_sok = round(total_sokocoin * processing_fee_rate, 2)
    if processing_fee_sok < 0:
        processing_fee_sok = 0.0
    include_shipping = bool(getattr(order_data, "include_shipping", False))
    shipping_fee_sok = 0.0
    shipping_distance_km = None
    total_charge_sok = total_sokocoin + processing_fee_sok
    
    # Check buyer's Sokocoin balance (including processing fee)
    # Group by seller (assuming one seller per order for simplicity)
    # In production, you might want to create separate orders per seller
    seller_id = order_items_data[0]["seller_id"]
    seller = db.query(User).filter(User.id == seller_id).first()
    if not seller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller not found"
        )
    
    # Get seller wallet
    order_currency_code = (default_currency or "TZS")
    seller_wallet = _get_or_create_wallet(seller_id, db)
    seller_currency_code = seller_amounts[seller_id].get("currency", order_currency_code)
    seller_gross_sokocoin_amount = seller_amounts[seller_id]["sokocoin"]
    seller_net_sokocoin_amount = seller_gross_sokocoin_amount
    seller_gross_local_amount = seller_amounts[seller_id]["local"]
    seller_net_local_amount = seller_gross_local_amount

    if include_shipping:
        if current_user.latitude is None or current_user.longitude is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add your address with location details before selecting Sokoni Africa logistics."
            )
        if seller.latitude is None or seller.longitude is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seller has not provided a pickup location yet. Contact the seller for delivery arrangements."
            )
        shipping_distance_km = _calculate_distance(
            current_user.latitude,
            current_user.longitude,
            seller.latitude,
            seller.longitude,
        )
        if shipping_distance_km is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to calculate shipping distance. Try again later."
            )
        shipping_fee_sok = _calculate_shipping_fee(shipping_distance_km)
        total_charge_sok += shipping_fee_sok

    if buyer_wallet.sokocoin_balance < total_charge_sok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient Sokocoin balance. Required: {total_charge_sok:.2f} SOK, Available: {buyer_wallet.sokocoin_balance:.2f} SOK"
        )
    
    # Create order
    db_order = Order(
        customer_id=current_user.id,
        seller_id=seller_id,
        total_amount=total_charge_sok,
        processing_fee=processing_fee_sok,
        shipping_fee=shipping_fee_sok,
        shipping_distance_km=shipping_distance_km,
        includes_shipping=include_shipping,
        shipping_address=order_data.shipping_address,
        payment_method=order_data.payment_method or "sokocoin",
        status=OrderStatus.PENDING,
        payment_status="held"  # Funds remain held until buyer confirms delivery
    )
    
    db.add(db_order)
    db.flush()
    
    # Create order items
    for item_data in order_items_data:
        db_order_item = OrderItem(
            order_id=db_order.id,
            product_id=item_data["product_id"],
            quantity=item_data["quantity"],
            price=item_data["price"]
        )
        db.add(db_order_item)
    
    # Process Sokocoin payment
    # 1. Deduct from buyer's wallet
    buyer_wallet.sokocoin_balance -= total_charge_sok
    buyer_wallet.total_spent = (buyer_wallet.total_spent or 0.0) + total_charge_sok
    
    # 2. Create buyer's purchase transaction
    buyer_transaction = WalletTransaction(
        wallet_id=buyer_wallet.id,
        user_id=current_user.id,
        transaction_type=WalletTransactionType.PURCHASE,
        status=WalletTransactionStatus.COMPLETED,
        sokocoin_amount=total_charge_sok,
        local_currency_amount=total_local_amount,
        local_currency_code=order_currency_code,
        exchange_rate=_get_exchange_rate(order_currency_code),
        payment_gateway="sokocoin",
        description=f"Purchase - Order #{db_order.id}",
        completed_at=datetime.now(timezone.utc),
        extra_data={
            "order_id": db_order.id,
            "products_subtotal_sok": total_sokocoin,
            "processing_fee_sok": processing_fee_sok,
            "processing_fee_rate": processing_fee_rate,
            "shipping_fee_sok": shipping_fee_sok,
            "shipping_distance_km": shipping_distance_km,
            "includes_shipping": include_shipping,
        }
    )
    db.add(buyer_transaction)
    
    # 3. Record seller's pending transaction (funds released after delivery confirmation)
    release_reference = f"ORDER-{db_order.id}-RELEASE"
    seller_gross_sokocoin_amount = seller_amounts[seller_id]["sokocoin"]
    seller_net_sokocoin_amount = seller_gross_sokocoin_amount
    seller_transaction = WalletTransaction(
        wallet_id=seller_wallet.id,
        user_id=seller_id,
        transaction_type=WalletTransactionType.EARN,
        status=WalletTransactionStatus.PENDING,
        sokocoin_amount=seller_net_sokocoin_amount,
        local_currency_amount=seller_net_local_amount,
        local_currency_code=seller_currency_code,
        exchange_rate=_get_exchange_rate(seller_currency_code),
        payment_gateway="sokocoin",
        payment_reference=release_reference,
        description=(
            f"Sale pending release - Order #{db_order.id} from {current_user.username}."
        ),
        extra_data={
            "order_id": db_order.id,
            "seller_id": seller_id,
            "buyer_id": current_user.id,
            "seller_local_amount": seller_net_local_amount,
            "seller_local_gross_amount": seller_gross_local_amount,
            "seller_sokocoin_amount": seller_gross_sokocoin_amount,
            "seller_gross_sokocoin_amount": seller_gross_sokocoin_amount,
            "processing_fee_sok": processing_fee_sok,
            "processing_fee_rate": processing_fee_rate,
            "seller_currency": seller_currency_code,
            "release_on": "delivery_confirmation"
        }
    )
    db.add(seller_transaction)
    
    # Clear cart
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    
    # Create notifications
    # Notification for seller about new order
    seller_notification = Notification(
        user_id=seller_id,
        notification_type="order",
        title="New Order",
        message=(
            f"{current_user.username} placed an order for {len(order_items_data)} item(s). "
            f"{seller_gross_sokocoin_amount:.2f} SOK will be released once the buyer confirms delivery."
        ),
        related_user_id=current_user.id,
        related_order_id=db_order.id
    )
    db.add(seller_notification)
    
    # Notification for buyer about successful purchase
    buyer_notification = Notification(
        user_id=current_user.id,
        notification_type="order",
        title="Order Placed",
        message=(
            f"Your order #{db_order.id} has been placed successfully. "
            f"{total_charge_sok:.2f} SOK deducted from your wallet "
            f"(includes {processing_fee_sok:.2f} SOK processing fee). "
            "Confirm delivery once you receive your items to release payment to the seller."
        ),
        related_order_id=db_order.id
    )
    db.add(buyer_notification)
    
    db.commit()
    db.refresh(db_order)
    
    # Build response
    order_response = _build_order_response(db_order, db)
    if not order_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare order response"
        )
    return order_response


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update order status"""
    order = (
        db.query(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Only seller can update status
    if order.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only seller can update order status"
        )
    
    order.status = new_status
    db.commit()
    db.refresh(order)
    
    # Create notification for customer about order status change
    customer = db.query(User).filter(User.id == order.customer_id).first()
    if customer:
        status_messages = {
            OrderStatus.PENDING: "is pending",
            OrderStatus.CONFIRMED: "has been confirmed",
            OrderStatus.PROCESSING: "is being processed",
            OrderStatus.SHIPPED: "has been shipped",
            OrderStatus.DELIVERED: "has been delivered",
            OrderStatus.CANCELLED: "has been cancelled"
        }
        status_message = status_messages.get(new_status, "status has been updated")
        
        notification = Notification(
            user_id=order.customer_id,
            notification_type="order",
            title="Order Status Updated",
            message=f"Your order #{order.id} {status_message}",
            related_user_id=current_user.id,
            related_order_id=order.id
        )
        db.add(notification)
        db.commit()
    
    order_response = _build_order_response(order, db, seller_id=current_user.id)
    if not order_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare order response"
        )
    return order_response


@router.post("/{order_id}/confirm-delivery", response_model=OrderResponse)
async def confirm_delivery(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Allow the buyer to confirm delivery and release payment to the seller"""
    order = (
        db.query(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the buyer can confirm delivery for this order"
        )

    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order was cancelled and cannot be confirmed"
        )

    if order.status == OrderStatus.DELIVERED:
        order_response = _build_order_response(order, db)
        if not order_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to prepare order response"
            )
        return order_response

    if order.status not in {OrderStatus.SHIPPED, OrderStatus.CONFIRMED, OrderStatus.PROCESSING}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be shipped before it can be confirmed as delivered"
        )

    if (order.payment_status or "").lower() in {"paid", "released"}:
        order.status = OrderStatus.DELIVERED
        order.payment_status = "released"
        order.updated_at = datetime.now(timezone.utc)

        seller_notification = Notification(
            user_id=order.seller_id,
            notification_type="order",
            title="Order Delivered",
            message=(
                f"{current_user.username} confirmed delivery for order #{order.id}. "
                "Payment was already released to your wallet."
            ),
            related_user_id=current_user.id,
            related_order_id=order.id,
        )
        db.add(seller_notification)

        buyer_notification = Notification(
            user_id=current_user.id,
            notification_type="order",
            title="Delivery Confirmed",
            message=f"You confirmed delivery for order #{order.id}. Thank you for shopping with Sokoni Africa!",
            related_order_id=order.id,
        )
        db.add(buyer_notification)

        db.commit()
        db.refresh(order)
        order_response = _build_order_response(order, db)
        if not order_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to prepare order response"
            )
        return order_response

    seller_wallet = _get_or_create_wallet(order.seller_id, db)
    release_reference = f"ORDER-{order.id}-RELEASE"
    seller_transaction = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.user_id == order.seller_id,
            WalletTransaction.transaction_type == WalletTransactionType.EARN,
            WalletTransaction.payment_reference == release_reference
        )
        .order_by(WalletTransaction.created_at.desc())
        .first()
    )

    release_amount = 0.0
    seller_local_amount = 0.0

    if seller_transaction:
        extra = seller_transaction.extra_data or {}
        release_amount = float(extra.get("seller_sokocoin_amount") or seller_transaction.sokocoin_amount or 0.0)
        seller_local_amount = float(extra.get("seller_local_amount") or seller_transaction.local_currency_amount or 0.0)

        now = datetime.now(timezone.utc)
        seller_wallet.sokocoin_balance += release_amount
        seller_wallet.total_earned = (seller_wallet.total_earned or 0.0) + release_amount

        seller_transaction.sokocoin_amount = release_amount
        seller_transaction.local_currency_amount = seller_local_amount or seller_transaction.local_currency_amount
        seller_transaction.status = WalletTransactionStatus.COMPLETED
        seller_transaction.completed_at = now
        extra.update(
            {
                "delivery_confirmed_by": current_user.id,
                "delivery_confirmed_at": now.isoformat(),
                "seller_sokocoin_amount": release_amount,
                "seller_local_amount": seller_local_amount,
            }
        )
        seller_transaction.extra_data = extra
    else:
        default_currency = next(
            (
                (item.product.local_currency or "TZS").upper()
                for item in order.items
                if getattr(item.product, "local_currency", None)
            ),
            "TZS",
        )
        seller_local_amount = 0.0
        release_amount = 0.0
        for item in order.items:
            item_currency = (getattr(item.product, "local_currency", None) or default_currency).upper()
            local_unit_price = getattr(item.product, "local_price", None)
            if local_unit_price is None:
                local_unit_price = _convert_from_sokocoin(item.price or 0.0, item_currency)
            sok_unit_price = item.price or _convert_to_sokocoin(local_unit_price, item_currency)
            quantity = item.quantity or 1
            seller_local_amount += local_unit_price * quantity
            release_amount += sok_unit_price * quantity

        now = datetime.now(timezone.utc)
        seller_wallet.sokocoin_balance += release_amount
        seller_wallet.total_earned = (seller_wallet.total_earned or 0.0) + release_amount

        seller_transaction = WalletTransaction(
            wallet_id=seller_wallet.id,
            user_id=order.seller_id,
            transaction_type=WalletTransactionType.EARN,
            status=WalletTransactionStatus.COMPLETED,
            sokocoin_amount=release_amount,
            local_currency_amount=seller_local_amount,
            local_currency_code=default_currency,
            exchange_rate=_get_exchange_rate(default_currency),
            payment_gateway="sokocoin",
            payment_reference=release_reference,
            description=f"Sale released - Order #{order.id} confirmed by {current_user.username}",
            completed_at=now,
            extra_data={
                "order_id": order.id,
                "seller_id": order.seller_id,
                "buyer_id": current_user.id,
            "seller_local_amount": seller_local_amount,
            "seller_sokocoin_amount": release_amount,
                "seller_currency": default_currency,
                "delivery_confirmed_by": current_user.id,
                "delivery_confirmed_at": now.isoformat(),
                "fallback_release": True,
            },
        )
        db.add(seller_transaction)

    order.status = OrderStatus.DELIVERED
    order.payment_status = "released"
    order.updated_at = datetime.now(timezone.utc)

    # Notify seller about delivery confirmation and payment release
    seller_notification = Notification(
        user_id=order.seller_id,
        notification_type="order",
        title="Order Delivered",
        message=(
            f"{current_user.username} confirmed delivery for order #{order.id}. "
            f"{release_amount:.2f} SOK has been released to your wallet."
        ),
        related_user_id=current_user.id,
        related_order_id=order.id,
    )
    db.add(seller_notification)

    # Notify buyer for confirmation
    buyer_notification = Notification(
        user_id=current_user.id,
        notification_type="order",
        title="Delivery Confirmed",
        message=f"You confirmed delivery for order #{order.id}. Thank you for shopping with Sokoni Africa!",
        related_order_id=order.id,
    )
    db.add(buyer_notification)

    db.commit()
    db.refresh(order)

    order_response = _build_order_response(order, db)
    if not order_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare order response"
        )
    return order_response


@router.post("/{order_id}/confirm-delivery", response_model=OrderResponse)
async def confirm_delivery(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Buyer confirms delivery, releasing funds to the seller."""
    order = (
        db.query(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the buyer can confirm delivery for this order"
        )

    if order.status == OrderStatus.DELIVERED:
        return _build_order_response(order, db)

    if order.status not in {OrderStatus.SHIPPED, OrderStatus.CONFIRMED, OrderStatus.PROCESSING}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be confirmed yet. Please wait for the seller to ship it."
        )

    release_reference = f"ORDER-{order.id}-RELEASE"
    seller_wallet = _get_or_create_wallet(order.seller_id, db)
    seller_transaction = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == seller_wallet.id,
            WalletTransaction.transaction_type == WalletTransactionType.EARN,
            WalletTransaction.payment_reference == release_reference,
        )
        .order_by(WalletTransaction.created_at.desc())
        .first()
    )

    if seller_transaction:
        if seller_transaction.status == WalletTransactionStatus.PENDING:
            seller_wallet.sokocoin_balance += seller_transaction.sokocoin_amount
            seller_wallet.total_earned = (seller_wallet.total_earned or 0.0) + seller_transaction.sokocoin_amount
            seller_transaction.status = WalletTransactionStatus.COMPLETED
            seller_transaction.completed_at = datetime.now(timezone.utc)
            seller_transaction.description = (
                f"Sale released - Order #{order.id} confirmed by {current_user.username}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment for this order has already been released."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No pending payment found to release for this order"
        )

    order.status = OrderStatus.DELIVERED
    order.payment_status = "released"
    db.commit()
    db.refresh(order)

    # Notify seller of payment release
    notification = Notification(
        user_id=order.seller_id,
        notification_type="order",
        title="Payment Released",
        message=(
            f"Buyer {current_user.username} confirmed delivery for order #{order.id}. "
            f"{seller_transaction.sokocoin_amount:.2f} SOK has been added to your wallet."
        ),
        related_user_id=current_user.id,
        related_order_id=order.id
    )
    db.add(notification)

    # Notify buyer of successful confirmation
    buyer_notification = Notification(
        user_id=current_user.id,
        notification_type="order",
        title="Delivery Confirmed",
        message=(
            f"Thank you! You confirmed delivery for order #{order.id}. "
            "Payment has been released to the seller."
        ),
        related_order_id=order.id
    )
    db.add(buyer_notification)
    db.commit()

    order_response = _build_order_response(order, db)
    if not order_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare order response"
        )
    return order_response


def _build_order_response(order: Order, db: Session, seller_id: Optional[int] = None) -> Optional[OrderResponse]:
    def _ensure_list(value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if v is not None]
        return [str(value)]

    order_dict = {k: v for k, v in order.__dict__.items() if not k.startswith("_")}
    # Ensure core fields always present
    order_dict["id"] = order.id
    order_dict["created_at"] = order.created_at
    order_dict["updated_at"] = order.updated_at
    order_dict["shipping_address"] = order.shipping_address or ""
    order_dict["payment_method"] = order.payment_method or "sokocoin"
    order_dict["payment_status"] = order.payment_status or "pending"
    order_dict["customer_id"] = order.customer_id
    order_dict["seller_id"] = seller_id if seller_id is not None else order.seller_id
    order_dict["status"] = order.status
    order_dict["shipping_fee"] = float(getattr(order, "shipping_fee", 0.0) or 0.0)
    order_dict["shipping_cost"] = order_dict["shipping_fee"]
    order_dict["shipping_distance_km"] = float(getattr(order, "shipping_distance_km", 0.0) or 0.0) if getattr(order, "shipping_distance_km", None) is not None else None
    order_dict["includes_shipping"] = bool(getattr(order, "includes_shipping", False))
    
    numeric_fields = ("shipping_cost", "shipping_fee", "tax", "discount", "processing_fee")
    for field in numeric_fields:
        value = order_dict.get(field)
        if value is None:
            order_dict[field] = 0.0
        else:
            try:
                order_dict[field] = float(value)
            except Exception:
                order_dict[field] = 0.0
    
    customer = db.query(User).filter(User.id == order.customer_id).first() if order.customer_id else None
    if customer:
        order_dict["customer_username"] = customer.username
        order_dict["customer_full_name"] = (customer.full_name or "").strip() or customer.username
        order_dict["customer_profile_image"] = customer.profile_image
        order_dict["customer_email"] = customer.email
        order_dict["customer_phone"] = customer.phone
    
    items = []
    seller_total_sok = 0.0
    for item in order.items:
        product = getattr(item, "product", None)
        if product is None:
            product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            continue
        
        if seller_id is not None and product.seller_id != seller_id:
            continue
        
        seller = getattr(product, "seller", None)
        if seller is None:
            seller = db.query(User).filter(User.id == product.seller_id).first()
        item_dict = {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        try:
            item_dict["price"] = float(item_dict.get("price", 0.0) or 0.0)
        except Exception:
            item_dict["price"] = 0.0
        try:
            item_dict["quantity"] = int(item_dict.get("quantity", 1) or 1)
        except Exception:
            item_dict["quantity"] = 1
        product_dict = {k: v for k, v in product.__dict__.items() if not k.startswith("_")}
        product_dict["tags"] = _ensure_list(product_dict.get("tags"))
        product_dict["images"] = _ensure_list(product_dict.get("images"))
        product_dict["is_sponsored"] = product_dict.get("is_sponsored", False)
        product_dict["is_winga_enabled"] = product_dict.get("is_winga_enabled", False)
        product_dict["has_warranty"] = product_dict.get("has_warranty", False)
        product_dict["is_private"] = product_dict.get("is_private", False)
        product_dict["is_adult_content"] = product_dict.get("is_adult_content", False)
        product_dict["local_price"] = product.local_price
        product_dict["local_currency"] = product.local_currency
        product_dict.update({
                    "seller_username": seller.username if seller else "Unknown",
            "seller_location": getattr(seller, "location_address", None),
                    "seller_profile_image": seller.profile_image if seller else None
        })
        item_dict["product"] = product_dict
        
        quantity = item.quantity or 1
        seller_total_sok += item_dict["price"] * int(quantity)
        
        items.append(OrderItemResponse(**item_dict))
    
    if seller_id is not None:
        if not items:
            return None
        order_dict["total_amount"] = float(seller_total_sok)
    else:
        existing_total = order_dict.get("total_amount")
        if existing_total is None:
            order_dict["total_amount"] = float(seller_total_sok)
        else:
            try:
                order_dict["total_amount"] = float(existing_total)
            except Exception:
                order_dict["total_amount"] = float(seller_total_sok)
    
    order_dict["items"] = items
    return OrderResponse(**order_dict)

