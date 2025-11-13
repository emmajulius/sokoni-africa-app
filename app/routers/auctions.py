"""
Auction router for handling live auction functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import math

from database import get_db
from models import Product, Bid, User, Wallet, Notification, WalletTransaction, WalletTransactionType, WalletTransactionStatus, CartItem
from schemas import BidCreate, BidResponse, AuctionResponse
from app.routers.auth import get_current_user
from config import settings
from app.routers.orders import _calculate_shipping_fee, _calculate_distance

router = APIRouter(prefix="/auctions", tags=["auctions"])


def _calculate_time_remaining(auction_end_time: datetime) -> int:
    """Calculate time remaining in seconds until auction ends"""
    if auction_end_time is None:
        return 0
    now = datetime.now(timezone.utc)
    if auction_end_time.tzinfo is None:
        auction_end_time = auction_end_time.replace(tzinfo=timezone.utc)
    remaining = (auction_end_time - now).total_seconds()
    return max(0, int(remaining))


def _cleanup_expired_auctions(db: Session, force: bool = False) -> int:
    """
    Delete auction products that ended more than 24 hours ago. 
    Returns count of deleted products.
    
    Args:
        db: Database session
        force: If True, always run cleanup. If False, only run occasionally (10% chance)
    """
    # Only run cleanup occasionally to avoid performance issues (unless forced)
    if not force:
        import random
        if random.random() >= 0.1:  # 90% chance to skip
            return 0
    
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(hours=24)
    
    # Find ended auctions that ended more than 24 hours ago
    expired_auctions = db.query(Product).filter(
        Product.is_auction == True,
        Product.auction_status == "ended",
        Product.auction_end_time <= cutoff_time
    ).all()
    
    if not expired_auctions:
        return 0
    
    deleted_count = 0
    for product in expired_auctions:
        try:
            # Delete related records
            from models import ProductLike, ProductComment, ProductRating, Bid, CartItem
            from app.routers.products import _delete_product_files
            
            # Delete engagement records
            db.query(ProductLike).filter(ProductLike.product_id == product.id).delete()
            db.query(ProductComment).filter(ProductComment.product_id == product.id).delete()
            db.query(ProductRating).filter(ProductRating.product_id == product.id).delete()
            
            # Delete bids
            db.query(Bid).filter(Bid.product_id == product.id).delete()
            
            # Remove from carts (if still in any cart)
            db.query(CartItem).filter(CartItem.product_id == product.id).delete()
            
            # Delete product files
            _delete_product_files(product)
            
            # Delete the product
            db.delete(product)
            deleted_count += 1
            print(f"Deleted expired auction product: {product.id} - {product.title} (ended {product.auction_end_time})")
        except Exception as e:
            print(f"Error deleting expired auction product {product.id}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if deleted_count > 0:
        db.commit()
        print(f"Cleaned up {deleted_count} expired auction product(s)")
    
    return deleted_count


def _check_and_update_auction_status(product: Product, db: Session) -> str:
    """Check auction status and update if needed. Returns current status."""
    now = datetime.now(timezone.utc)
    
    # Cleanup expired auctions (24 hours after end) - do this periodically
    _cleanup_expired_auctions(db, force=False)
    
    # Ensure auction_end_time is timezone-aware
    if product.auction_end_time:
        if product.auction_end_time.tzinfo is None:
            product.auction_end_time = product.auction_end_time.replace(tzinfo=timezone.utc)
        
        # If auction has ended, mark as ended and set winner
        if product.auction_status == "active" and now >= product.auction_end_time:
            product.auction_status = "ended"
            
            # Set winner if there are bids
            if product.current_bidder_id:
                product.winner_id = product.current_bidder_id
                
                # Update product price to winning bid amount for cart/order processing
                if product.current_bid:
                    product.price = product.current_bid
                
                # Automatically add product to winner's cart
                existing_cart_item = db.query(CartItem).filter(
                    CartItem.user_id == product.winner_id,
                    CartItem.product_id == product.id
                ).first()
                
                if not existing_cart_item:
                    # Add to winner's cart
                    cart_item = CartItem(
                        user_id=product.winner_id,
                        product_id=product.id,
                        quantity=1
                    )
                    db.add(cart_item)
                
                # Create notification for winner
                winner_notification = Notification(
                    user_id=product.winner_id,
                    notification_type="auction",
                    title="You Won the Auction!",
                    message=f"Congratulations! You won the auction for '{product.title}'. The item has been added to your cart. Please complete payment to secure your purchase.",
                    related_product_id=product.id,
                    is_read=False
                )
                db.add(winner_notification)
                
                # Notify seller
                seller_notification = Notification(
                    user_id=product.seller_id,
                    notification_type="auction",
                    title="Auction Ended",
                    message=f"Your auction for '{product.title}' has ended. Winner: User ID {product.winner_id}. Waiting for payment.",
                    related_product_id=product.id,
                    is_read=False
                )
                db.add(seller_notification)
                
                # Notify other bidders (those who were outbid)
                outbid_bidders = db.query(Bid.bidder_id).filter(
                    Bid.product_id == product.id,
                    Bid.bidder_id != product.winner_id,
                    Bid.is_outbid == False
                ).distinct().all()
                
                for (bidder_id,) in outbid_bidders:
                    outbid_notification = Notification(
                        user_id=bidder_id,
                        notification_type="auction",
                        title="Auction Ended",
                        message=f"The auction for '{product.title}' has ended. You were outbid.",
                        related_product_id=product.id,
                        is_read=False
                    )
                    db.add(outbid_notification)
                
                db.commit()
            
            return "ended"
        elif product.auction_status == "pending" and product.auction_start_time:
            # Check if auction should start
            if product.auction_start_time.tzinfo is None:
                product.auction_start_time = product.auction_start_time.replace(tzinfo=timezone.utc)
            
            if now >= product.auction_start_time:
                product.auction_status = "active"
                db.commit()
                return "active"
    
    return product.auction_status


@router.get("/active", response_model=List[AuctionResponse])
async def get_active_auctions(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all active auctions"""
    now = datetime.now(timezone.utc)
    
    # Get active auctions
    auctions = db.query(Product).filter(
        Product.is_auction == True,
        Product.auction_status == "active",
        Product.auction_end_time > now
    ).order_by(desc(Product.auction_end_time)).offset(skip).limit(limit).all()
    
    results = []
    for product in auctions:
        # Update status if needed
        status = _check_and_update_auction_status(product, db)
        if status != "active":
            continue
        
        # Get bid count
        bid_count = db.query(func.count(Bid.id)).filter(Bid.product_id == product.id).scalar() or 0
        
        # Get current bidder info
        current_bidder_username = None
        if product.current_bidder_id:
            bidder = db.query(User).filter(User.id == product.current_bidder_id).first()
            current_bidder_username = bidder.username if bidder else None
        
        # Calculate time remaining
        time_remaining = _calculate_time_remaining(product.auction_end_time)
        
        results.append(AuctionResponse(
            product_id=product.id,
            product_title=product.title,
            product_image=product.image_url,
            starting_price=product.starting_price or 0,
            current_bid=product.current_bid,
            bid_increment=product.bid_increment or 0,
            auction_start_time=product.auction_start_time or product.created_at,
            auction_end_time=product.auction_end_time or product.created_at,
            auction_status=product.auction_status,
            time_remaining_seconds=time_remaining,
            bid_count=bid_count,
            current_bidder_id=product.current_bidder_id,
            current_bidder_username=current_bidder_username,
            winner_id=product.winner_id,
            winner_username=None
        ))
    
    return results


@router.get("/{product_id}", response_model=AuctionResponse)
async def get_auction_details(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get auction details by product ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if not product.is_auction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not an auction"
        )
    
    # Update status if needed
    auction_status = _check_and_update_auction_status(product, db)
    
    # Get bid count
    bid_count = db.query(func.count(Bid.id)).filter(Bid.product_id == product.id).scalar() or 0
    
    # Get current bidder info
    current_bidder_username = None
    if product.current_bidder_id:
        bidder = db.query(User).filter(User.id == product.current_bidder_id).first()
        current_bidder_username = bidder.username if bidder else None
    
    # Get winner info
    winner_username = None
    if product.winner_id:
        winner = db.query(User).filter(User.id == product.winner_id).first()
        winner_username = winner.username if winner else None
    
    # Calculate time remaining
    time_remaining = _calculate_time_remaining(product.auction_end_time)
    
    return AuctionResponse(
        product_id=product.id,
        product_title=product.title,
        product_image=product.image_url,
        starting_price=product.starting_price or 0,
        current_bid=product.current_bid,
        bid_increment=product.bid_increment or 0,
        auction_start_time=product.auction_start_time or product.created_at,
        auction_end_time=product.auction_end_time or product.created_at,
        auction_status=product.auction_status,
        time_remaining_seconds=time_remaining,
        bid_count=bid_count,
        current_bidder_id=product.current_bidder_id,
        current_bidder_username=current_bidder_username,
        winner_id=product.winner_id,
        winner_username=winner_username
    )


@router.get("/{product_id}/bids", response_model=List[BidResponse])
async def get_auction_bids(
    product_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get bid history for an auction"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if not product.is_auction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not an auction"
        )
    
    # Get bids ordered by bid time (most recent first)
    bids = db.query(Bid).filter(
        Bid.product_id == product_id
    ).order_by(desc(Bid.bid_time)).offset(skip).limit(limit).all()
    
    results = []
    for bid in bids:
        bidder = db.query(User).filter(User.id == bid.bidder_id).first()
        results.append(BidResponse(
            id=bid.id,
            product_id=bid.product_id,
            bidder_id=bid.bidder_id,
            bidder_username=bidder.username if bidder else "Unknown",
            bidder_profile_image=bidder.profile_image if bidder else None,
            bid_amount=bid.bid_amount,
            bid_time=bid.bid_time,
            is_winning_bid=bid.is_winning_bid,
            is_outbid=bid.is_outbid
        ))
    
    return results


@router.post("/{product_id}/bid", response_model=BidResponse)
async def place_bid(
    product_id: int,
    bid_data: BidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Place a bid on an auction"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if not product.is_auction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not an auction"
        )
    
    # Check if user is the seller
    if product.seller_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot bid on your own auction"
        )
    
    # Quick check if auction has ended (faster than full status update)
    now = datetime.now(timezone.utc)
    if product.auction_end_time:
        if product.auction_end_time.tzinfo is None:
            auction_end = product.auction_end_time.replace(tzinfo=timezone.utc)
        else:
            auction_end = product.auction_end_time
        
        # Quick check - if ended more than 1 hour ago, update status
        if auction_end < now - timedelta(hours=1):
            # Only update status if clearly ended
            if product.auction_status not in ("ended", "completed"):
                auction_status = _check_and_update_auction_status(product, db)
                db.refresh(product)
            else:
                auction_status = product.auction_status
        else:
            # Auction is still active or just ended - use current status
            auction_status = product.auction_status or "active"
        
        # Check if auction has ended
        if now >= auction_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction has ended"
            )
    else:
        # No end time - use current status
        auction_status = product.auction_status or "active"
    
    # Check auction status
    if auction_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot place bid. Auction status: {auction_status}"
        )
    
    # Calculate minimum bid
    if product.current_bid is None:
        # First bid - must be at least starting price
        min_bid = product.starting_price or 0
    else:
        # Subsequent bids - must be at least current_bid + bid_increment
        min_bid = product.current_bid + (product.bid_increment or 0)
    
    if bid_data.bid_amount < min_bid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bid amount must be at least {min_bid:.2f} Sokocoin"
        )
    
    # Check user's wallet balance
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet not found. Please contact support."
        )
    
    # For auctions, we'll hold the bid amount temporarily
    # The amount will only be charged if the user wins
    # For now, we'll just verify they have enough balance
    if wallet.sokocoin_balance < bid_data.bid_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. You have {wallet.sokocoin_balance:.2f} Sokocoin, but need {bid_data.bid_amount:.2f} Sokocoin"
        )
    
    # Mark previous winning bid as outbid (optimized - only if needed)
    if product.current_bidder_id and product.current_bidder_id != current_user.id:
        try:
            # Use a simpler query - just update the most recent winning bid
            previous_winning_bid = db.query(Bid).filter(
                Bid.product_id == product_id,
                Bid.bidder_id == product.current_bidder_id,
                Bid.is_winning_bid == True
            ).order_by(desc(Bid.bid_time)).first()
            
            if previous_winning_bid:
                previous_winning_bid.is_winning_bid = False
                previous_winning_bid.is_outbid = True
                
                # Notify previous bidder they were outbid (defer to background if possible)
                try:
                    outbid_notification = Notification(
                        user_id=product.current_bidder_id,
                        notification_type="auction",
                        title="You Were Outbid",
                        message=f"Someone placed a higher bid on '{product.title}'. Current bid: {bid_data.bid_amount:.2f} Sokocoin",
                        related_product_id=product.id,
                        is_read=False
                    )
                    db.add(outbid_notification)
                except Exception as e:
                    # If notification fails, continue anyway
                    print(f"Warning: Failed to create outbid notification: {e}")
        except Exception as e:
            # If bid update fails, log but continue
            print(f"Warning: Failed to update previous bid: {e}")
    
    # Create new bid
    new_bid = Bid(
        product_id=product_id,
        bidder_id=current_user.id,
        bid_amount=bid_data.bid_amount,
        is_winning_bid=True,
        is_outbid=False
    )
    db.add(new_bid)
    
    # Update product with new current bid
    product.current_bid = bid_data.bid_amount
    product.current_bidder_id = current_user.id
    product.updated_at = now
    
    # Notify seller of new bid (defer to background if possible)
    try:
        seller_notification = Notification(
            user_id=product.seller_id,
            notification_type="auction",
            title="New Bid Received",
            message=f"A new bid of {bid_data.bid_amount:.2f} Sokocoin was placed on '{product.title}'",
            related_product_id=product.id,
            related_user_id=current_user.id,
            is_read=False
        )
        db.add(seller_notification)
    except Exception as e:
        # If notification fails, continue anyway
        print(f"Warning: Failed to create seller notification: {e}")
    
    try:
        db.commit()
        db.refresh(new_bid)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place bid: {str(e)}"
        )
    
    # Get bidder info for response (already have current_user, no need to query)
    bidder = current_user
    
    return BidResponse(
        id=new_bid.id,
        product_id=new_bid.product_id,
        bidder_id=new_bid.bidder_id,
        bidder_username=bidder.username if bidder else "Unknown",
        bidder_profile_image=bidder.profile_image if bidder else None,
        bid_amount=new_bid.bid_amount,
        bid_time=new_bid.bid_time,
        is_winning_bid=new_bid.is_winning_bid,
        is_outbid=new_bid.is_outbid
    )


@router.post("/{product_id}/complete-payment")
async def complete_auction_payment(
    product_id: int,
    include_shipping: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Complete payment for a won auction"""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if not product.is_auction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not an auction"
        )
    
    # Check if auction has ended
    if product.auction_status != "ended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auction has not ended yet"
        )
    
    # Check if user is the winner
    if product.winner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the winner of this auction"
        )
    
    # Check if already paid
    if product.winner_paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already completed for this auction"
        )
    
    # Get winner's wallet
    winner_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not winner_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet not found"
        )
    
    # Calculate total amount
    total_amount = product.current_bid or product.starting_price or 0
    
    # Calculate shipping fee if requested
    shipping_fee = 0.0
    shipping_distance_km = None
    if include_shipping:
        # Get buyer and seller locations
        buyer = db.query(User).filter(User.id == current_user.id).first()
        seller = db.query(User).filter(User.id == product.seller_id).first()
        
        if buyer and seller and buyer.latitude and buyer.longitude and seller.latitude and seller.longitude:
            # Calculate distance using Haversine formula
            distance_km = _calculate_distance(
                seller.latitude, seller.longitude,
                buyer.latitude, buyer.longitude
            )
            if distance_km is not None:
                shipping_fee = _calculate_shipping_fee(distance_km)
                shipping_distance_km = distance_km
    
    # Calculate processing fee (2% of total)
    processing_fee = total_amount * settings.PROCESSING_FEE_RATE
    
    # Total charge
    total_charge = total_amount + shipping_fee + processing_fee
    
    # Check balance
    if winner_wallet.sokocoin_balance < total_charge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. You need {total_charge:.2f} Sokocoin but have {winner_wallet.sokocoin_balance:.2f} Sokocoin"
        )
    
    # Deduct from winner's wallet
    winner_wallet.sokocoin_balance -= total_charge
    winner_wallet.total_spent = (winner_wallet.total_spent or 0) + total_charge
    
    # Credit seller (only the product amount, not fees)
    seller_wallet = db.query(Wallet).filter(Wallet.user_id == product.seller_id).first()
    if seller_wallet:
        seller_wallet.sokocoin_balance += total_amount
        seller_wallet.total_earned = (seller_wallet.total_earned or 0) + total_amount
    
    # Create wallet transaction for winner
    winner_transaction = WalletTransaction(
        wallet_id=winner_wallet.id,
        user_id=current_user.id,
        transaction_type=WalletTransactionType.PURCHASE,
        status=WalletTransactionStatus.COMPLETED,
        sokocoin_amount=total_charge,
        description=f"Payment for auction win: {product.title}",
        completed_at=datetime.now(timezone.utc)
    )
    db.add(winner_transaction)
    
    # Create wallet transaction for seller
    if seller_wallet:
        seller_transaction = WalletTransaction(
            wallet_id=seller_wallet.id,
            user_id=product.seller_id,
            transaction_type=WalletTransactionType.EARN,
            status=WalletTransactionStatus.COMPLETED,
            sokocoin_amount=total_amount,
            description=f"Earning from auction sale: {product.title}",
            completed_at=datetime.now(timezone.utc)
        )
        db.add(seller_transaction)
    
    # Mark winner as paid
    product.winner_paid = True
    
    # Create order for the auction purchase
    from models import Order, OrderItem, OrderStatus
    order = Order(
        customer_id=current_user.id,
        seller_id=product.seller_id,
        status=OrderStatus.CONFIRMED,
        total_amount=total_amount,
        processing_fee=processing_fee,
        shipping_fee=shipping_fee,
        shipping_distance_km=shipping_distance_km,
        includes_shipping=include_shipping,
        shipping_address=current_user.location_address or "Address not provided",
        payment_method="sokocoin",
        payment_status="paid"
    )
    db.add(order)
    db.flush()
    
    # Create order item
    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=1,
        price=total_amount
    )
    db.add(order_item)
    
    # Create notifications
    winner_notification = Notification(
        user_id=current_user.id,
        notification_type="order",
        title="Payment Successful",
        message=f"Your payment for '{product.title}' has been processed successfully. Order ID: {order.id}",
        related_order_id=order.id,
        related_product_id=product.id,
        is_read=False
    )
    db.add(winner_notification)
    
    seller_notification = Notification(
        user_id=product.seller_id,
        notification_type="order",
        title="Auction Payment Received",
        message=f"The winner has completed payment for '{product.title}'. Order ID: {order.id}",
        related_order_id=order.id,
        related_product_id=product.id,
        is_read=False
    )
    db.add(seller_notification)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Payment completed successfully",
        "order_id": order.id,
        "total_amount": total_amount,
        "processing_fee": processing_fee,
        "shipping_fee": shipping_fee,
        "total_charge": total_charge
    }

