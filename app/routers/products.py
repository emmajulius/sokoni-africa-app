from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from typing import List, Optional
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
import math
import traceback
import logging
from database import get_db

logger = logging.getLogger(__name__)
from models import Product, User, Category, ProductLike, ProductComment, ProductRating, Notification, Bid
from schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductCommentCreate, ProductCommentResponse,
    ProductRatingCreate, ProductRatingResponse
)
from auth import get_current_user, get_current_active_user, get_current_user_optional, require_user_type
from models import UserType
from config import settings

router = APIRouter()


def _get_exchange_rate(currency: Optional[str]) -> float:
    currency_upper = (currency or "TZS").upper()
    if currency_upper == "TZS":
        return settings.SOKOCOIN_EXCHANGE_RATE_TZS
    if currency_upper == "KES":
        return settings.SOKOCOIN_EXCHANGE_RATE_KES
    if currency_upper == "NGN":
        return settings.SOKOCOIN_EXCHANGE_RATE_NGN
    return settings.SOKOCOIN_EXCHANGE_RATE_TZS


def _convert_to_sokocoin(local_amount: float, currency: Optional[str]) -> float:
    exchange_rate = _get_exchange_rate(currency)
    if exchange_rate <= 0:
        return local_amount
    return local_amount / exchange_rate


def _convert_from_sokocoin(sok_amount: float, currency: Optional[str]) -> float:
    exchange_rate = _get_exchange_rate(currency)
    return sok_amount * exchange_rate


def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula (returns kilometers)"""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return round(distance, 2)


def _calculate_product_engagement(product: Product, db: Session, current_user_id: Optional[int] = None) -> dict:
    """Calculate product engagement stats (likes, comments, rating)"""
    # Count likes
    likes_count = db.query(func.count(ProductLike.id)).filter(
        ProductLike.product_id == product.id
    ).scalar() or 0
    
    # Count comments
    comments_count = db.query(func.count(ProductComment.id)).filter(
        ProductComment.product_id == product.id
    ).scalar() or 0
    
    # Calculate average rating
    avg_rating = db.query(func.avg(ProductRating.rating)).filter(
        ProductRating.product_id == product.id
    ).scalar() or 0.0
    
    # Check if current user has liked this product
    is_liked = False
    if current_user_id:
        like = db.query(ProductLike).filter(
            ProductLike.product_id == product.id,
            ProductLike.user_id == current_user_id
        ).first()
        is_liked = like is not None
    
    return {
        'likes': likes_count,
        'comments': comments_count,
        'rating': float(avg_rating) if avg_rating else 0.0,
        'is_liked': is_liked
    }


def _extract_upload_path(url: Optional[str]) -> Optional[Path]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        path = parsed.path if parsed.scheme else url
        if not path:
            return None
        if path.startswith("/"):
            path = path[1:]
        prefixes = ("api/uploads/", "uploads/")
        for prefix in prefixes:
            if path.startswith(prefix):
                relative = path[len(prefix):]
                if relative:
                    return Path("uploads") / Path(relative)
        return None
    except Exception:
        return None


def _delete_product_files(product: Product) -> None:
    uploads_root = Path("uploads")
    if not uploads_root.exists():
        return

    candidate_urls: List[str] = []
    if getattr(product, "image_url", None):
        candidate_urls.append(product.image_url)
    if getattr(product, "images", None):
        candidate_urls.extend(product.images)

    for url in candidate_urls:
        file_path = _extract_upload_path(url)
        if not file_path:
            continue
        try:
            full_path = uploads_root / file_path.relative_to("uploads") if "uploads" in file_path.parts else uploads_root / file_path
            if full_path.exists():
                full_path.unlink()
        except Exception as exc:
            print(f"Warning: failed to delete file {url}: {exc}")


@router.get("", response_model=List[ProductResponse])
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    seller_id: Optional[int] = Query(None, description="Filter by seller ID"),
    latitude: Optional[float] = Query(None, description="User's latitude for location-based sorting"),
    longitude: Optional[float] = Query(None, description="User's longitude for location-based sorting"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),  # Reduced from 100 to 20 for faster loading
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get all products with optional filtering and location-based sorting"""
    try:
        # Skip auction cleanup on every request - it's too slow
        # Cleanup should be done via a background task or cron job
        
        # Use eager loading to prevent N+1 queries
        from sqlalchemy.orm import joinedload
        query = db.query(Product).options(joinedload(Product.seller))

        if category:
            query = query.filter(Product.category == category.lower())

        if seller_id:
            query = query.filter(Product.seller_id == seller_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Product.title.ilike(search_pattern),
                    Product.description.ilike(search_pattern)
                )
            )

        # Exclude expired auctions (ended more than 24 hours ago)
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=24)
        query = query.filter(
            or_(
                Product.is_auction == False,
                Product.auction_status != "ended",
                Product.auction_end_time > cutoff_time,
                Product.auction_end_time.is_(None)
            )
        )
        
        query = query.order_by(desc(Product.created_at))
        # Optimized: Only load the exact number needed for better performance
        # For location-based sorting, we still need a few extra to sort by distance
        # But reduce from +10 to +5 for faster queries
        products = query.offset(skip).limit(limit + 5 if latitude and longitude else limit).all()

        # Reduced logging for performance
        if len(products) > 0:
            print(f"GET PRODUCTS: Found {len(products)} products")

        result: List[ProductResponse] = []
        current_user_id = current_user.id if current_user else None

        user_lat = latitude
        user_lon = longitude
        if user_lat is None and user_lon is None and current_user:
            user_lat = current_user.latitude
            user_lon = current_user.longitude

        # Batch load engagement stats for all products at once (optimize N+1 queries)
        product_ids = [p.id for p in products]
        
        # Batch load likes count
        likes_counts = {}
        if product_ids:
            likes_data = db.query(
                ProductLike.product_id,
                func.count(ProductLike.id).label('count')
            ).filter(ProductLike.product_id.in_(product_ids)).group_by(ProductLike.product_id).all()
            likes_counts = {pid: count for pid, count in likes_data}
        
        # Batch load comments count
        comments_counts = {}
        if product_ids:
            comments_data = db.query(
                ProductComment.product_id,
                func.count(ProductComment.id).label('count')
            ).filter(ProductComment.product_id.in_(product_ids)).group_by(ProductComment.product_id).all()
            comments_counts = {pid: count for pid, count in comments_data}
        
        # Batch load ratings
        ratings_data = {}
        if product_ids:
            ratings_query = db.query(
                ProductRating.product_id,
                func.avg(ProductRating.rating).label('avg_rating')
            ).filter(ProductRating.product_id.in_(product_ids)).group_by(ProductRating.product_id).all()
            ratings_data = {pid: float(avg) if avg else 0.0 for pid, avg in ratings_query}
        
        # Batch load user likes (if authenticated)
        user_liked_products = set()
        if current_user_id and product_ids:
            user_likes = db.query(ProductLike.product_id).filter(
                ProductLike.product_id.in_(product_ids),
                ProductLike.user_id == current_user_id
            ).all()
            user_liked_products = {like[0] for like in user_likes}
        
        # Batch load bidders for auctions (simplified - skip status updates to avoid hanging)
        bidder_map = {}
        bid_counts_map = {}
        auction_product_ids = [p.id for p in products if p.is_auction]
        if auction_product_ids:
            try:
                # Batch load bid counts (skip status updates - they're too slow)
                bid_counts_data = db.query(
                    Bid.product_id,
                    func.count(Bid.id).label('count')
                ).filter(Bid.product_id.in_(auction_product_ids)).group_by(Bid.product_id).all()
                bid_counts_map = {pid: count for pid, count in bid_counts_data}
                
                # Batch load current bidders
                current_bidder_ids = {p.id: p.current_bidder_id for p in products if p.is_auction and p.current_bidder_id}
                if current_bidder_ids:
                    bidder_user_ids = list(set(current_bidder_ids.values()))
                    bidders = db.query(User.id, User.username).filter(User.id.in_(bidder_user_ids)).all()
                    bidder_username_map = {uid: username for uid, username in bidders}
                    bidder_map = {pid: bidder_username_map.get(bidder_id) for pid, bidder_id in current_bidder_ids.items()}
            except Exception as e:
                print(f"Warning: Failed to load auction data: {e}")
                # Continue without auction data rather than failing

        for product in products:
            # Use eager-loaded seller (no additional query)
            seller = product.seller if hasattr(product, 'seller') else None
            if not seller:
                try:
                    seller = db.query(User).filter(User.id == product.seller_id).first()
                except Exception as e:
                    print(f"ERROR: Failed to load seller for product {product.id}: {e}")
                    seller = None

            # Use batch-loaded engagement stats
            engagement = {
                'likes': likes_counts.get(product.id, 0),
                'comments': comments_counts.get(product.id, 0),
                'rating': ratings_data.get(product.id, 0.0),
                'is_liked': product.id in user_liked_products,
            }

            distance = None
            try:
                if user_lat is not None and user_lon is not None and seller:
                    if seller.latitude is not None and seller.longitude is not None:
                        distance = _calculate_distance(
                            user_lat, user_lon,
                            seller.latitude, seller.longitude
                        )
            except Exception as e:
                print(f"ERROR: Failed to calculate distance for product {product.id}: {e}")
                traceback.print_exc()
                distance = None

            # Calculate auction fields if it's an auction (using batch-loaded data)
            time_remaining_seconds = None
            bid_count = None
            current_bidder_username = None
            if product.is_auction:
                try:
                    # Status already updated in batch above, just refresh if needed
                    if product.auction_end_time:
                        now = datetime.now(timezone.utc)
                        if product.auction_end_time.tzinfo is None:
                            auction_end = product.auction_end_time.replace(tzinfo=timezone.utc)
                        else:
                            auction_end = product.auction_end_time
                        remaining = (auction_end - now).total_seconds()
                        time_remaining_seconds = max(0, int(remaining))
                    
                    # Use batch-loaded bid count
                    bid_count = bid_counts_map.get(product.id, 0)
                    
                    # Use batch-loaded bidder username
                    current_bidder_username = bidder_map.get(product.id)
                except Exception as e:
                    print(f"ERROR: Failed to calculate auction fields for product {product.id}: {e}")
                    traceback.print_exc()

            try:
                product_dict = {
                    "id": product.id,
                    "title": product.title,
                    "description": product.description,
                    "price": float(product.price) if product.price is not None else 0.0,
                    "local_price": float(product.local_price) if product.local_price is not None else None,
                    "local_currency": product.local_currency,
                    "category": product.category,
                    "unit_type": product.unit_type,
                    "stock_quantity": product.stock_quantity,
                    "is_winga_enabled": product.is_winga_enabled,
                    "has_warranty": product.has_warranty,
                    "is_private": product.is_private,
                    "is_adult_content": product.is_adult_content,
                    "tags": product.tags if product.tags else [],
                    "seller_id": product.seller_id,
                    "seller_username": seller.username if seller else "Unknown",
                    "seller_location": getattr(seller, "location_address", None) if seller else None,
                    "seller_profile_image": getattr(seller, "profile_image", None) if seller else None,
                    "image_url": product.image_url,
                    "images": product.images if product.images else [],
                    "likes": engagement['likes'],
                    "comments": engagement['comments'],
                    "rating": engagement['rating'],
                    "distance": distance,
                    "is_liked": engagement['is_liked'],
                    "is_sponsored": product.is_sponsored,
                    # Auction fields
                    "is_auction": product.is_auction or False,
                    "starting_price": float(product.starting_price) if product.starting_price is not None else None,
                    "bid_increment": float(product.bid_increment) if product.bid_increment is not None else None,
                    # Convert to int if it's a whole number (for backward compatibility with int schema)
                    "auction_duration_hours": int(product.auction_duration_hours) if product.auction_duration_hours is not None and product.auction_duration_hours == int(product.auction_duration_hours) else product.auction_duration_hours,
                    "auction_start_time": product.auction_start_time,
                    "auction_end_time": product.auction_end_time,
                    "current_bid": float(product.current_bid) if product.current_bid is not None else None,
                    "current_bidder_id": product.current_bidder_id,
                    "current_bidder_username": current_bidder_username,
                    "auction_status": product.auction_status,
                    "winner_id": product.winner_id,
                    "winner_paid": product.winner_paid if product.winner_paid is not None else False,
                    "bid_count": bid_count,
                    "time_remaining_seconds": time_remaining_seconds,
                    "created_at": product.created_at,
                    "updated_at": product.updated_at,
                }
                result.append(ProductResponse(**product_dict))
            except Exception as e:
                print(f"ERROR: Error converting product {product.id}: {e}")
                traceback.print_exc()
                continue

        if user_lat is not None and user_lon is not None:
            result.sort(key=lambda x: (x.distance is None, x.distance or float('inf')))

        result = result[:limit]
        print(f"SUCCESS: Returning {len(result)} products")
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"FATAL: Unhandled error in get_products: {e}")
        traceback.print_exc()
        # Return empty list instead of crashing to prevent hanging
        logger.error(f"Error in get_products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading products: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get product by ID with real-time engagement stats"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    seller = db.query(User).filter(User.id == product.seller_id).first()
    
    # Calculate real-time engagement stats
    current_user_id = current_user.id if current_user else None
    engagement = _calculate_product_engagement(product, db, current_user_id)
    
    # Calculate auction time remaining if it's an auction
    time_remaining_seconds = None
    bid_count = None
    current_bidder_username = None
    
    if product.is_auction:
        # Update auction status
        from app.routers.auctions import _check_and_update_auction_status
        _check_and_update_auction_status(product, db)
        db.refresh(product)
        
        if product.auction_end_time:
            now = datetime.now(timezone.utc)
            if product.auction_end_time.tzinfo is None:
                auction_end = product.auction_end_time.replace(tzinfo=timezone.utc)
            else:
                auction_end = product.auction_end_time
            remaining = (auction_end - now).total_seconds()
            time_remaining_seconds = max(0, int(remaining))
        
        # Get bid count
        bid_count = db.query(func.count(Bid.id)).filter(Bid.product_id == product.id).scalar() or 0
        
        # Get current bidder username
        if product.current_bidder_id:
            bidder = db.query(User).filter(User.id == product.current_bidder_id).first()
            current_bidder_username = bidder.username if bidder else None
    
    product_dict = {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "local_price": product.local_price,
        "local_currency": product.local_currency,
        "category": product.category,
        "unit_type": product.unit_type,
        "stock_quantity": product.stock_quantity,
        "is_winga_enabled": product.is_winga_enabled,
        "has_warranty": product.has_warranty,
        "is_private": product.is_private,
        "is_adult_content": product.is_adult_content,
        "tags": product.tags if product.tags else [],
        "seller_id": product.seller_id,
        "seller_username": seller.username if seller else "Unknown",
        "seller_location": getattr(seller, "location_address", None) if seller else None,
        "seller_profile_image": seller.profile_image if seller else None,
        "image_url": product.image_url if product.image_url else None,
        "images": [img for img in (product.images or []) if img] if product.images else [],
        "likes": engagement['likes'],
        "comments": engagement['comments'],
        "rating": engagement['rating'],
        "is_liked": engagement['is_liked'],
        "is_sponsored": product.is_sponsored,
        # Auction fields
        "is_auction": product.is_auction or False,
        "starting_price": product.starting_price,
        "bid_increment": product.bid_increment,
        # Convert to int if it's a whole number (for backward compatibility with int schema)
        "auction_duration_hours": int(product.auction_duration_hours) if product.auction_duration_hours is not None and product.auction_duration_hours == int(product.auction_duration_hours) else product.auction_duration_hours,
        "auction_start_time": product.auction_start_time,
        "auction_end_time": product.auction_end_time,
        "current_bid": product.current_bid,
        "current_bidder_id": product.current_bidder_id,
        "current_bidder_username": current_bidder_username,
        "auction_status": product.auction_status,
        "winner_id": product.winner_id,
        "winner_paid": product.winner_paid,
        "bid_count": bid_count,
        "time_remaining_seconds": time_remaining_seconds,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }
    
    return ProductResponse(**product_dict)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(require_user_type(UserType.SUPPLIER, UserType.RETAILER)),
    db: Session = Depends(get_db)
):
    """Create a new product (suppliers and retailers only)"""
    try:
        print(f"\n{'='*60}")
        print(f"CREATING PRODUCT")
        print(f"{'='*60}")
        print(f"Title: {product_data.title}")
        print(f"Price: {product_data.price}")
        print(f"Currency: {getattr(product_data, 'currency', 'N/A')}")
        print(f"Category: {product_data.category}")
        print(f"Is Auction: {getattr(product_data, 'is_auction', False)}")
        print(f"Seller ID: {current_user.id}")
        print(f"{'='*60}\n")
        
        # Verify category exists
        category = db.query(Category).filter(Category.slug == product_data.category.lower()).first()
        if not category:
            print(f"ERROR: Category '{product_data.category}' not found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{product_data.category}' not found"
            )
        
        # Check if this is an auction product
        is_auction = getattr(product_data, 'is_auction', False) or False
        if isinstance(is_auction, str):
            is_auction = is_auction.lower() in ['true', '1', 'yes']
        
        # Initialize auction duration (will be set if is_auction is True)
        auction_duration_hours = None
        
        if is_auction:
            # Validate auction fields
            if not product_data.starting_price or product_data.starting_price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Starting price is required for auction products and must be greater than 0"
                )
            if not product_data.bid_increment or product_data.bid_increment <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bid increment is required for auction products and must be greater than 0"
                )
            # Handle auction duration - prefer minutes, fallback to hours for backward compatibility
            if product_data.auction_duration_minutes is not None:
                if product_data.auction_duration_minutes < 1 or product_data.auction_duration_minutes > 43200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Auction duration must be between 1 and 43200 minutes (720 hours)"
                    )
                auction_duration_hours = product_data.auction_duration_minutes / 60.0
            elif product_data.auction_duration_hours is not None:
                if product_data.auction_duration_hours <= 0.016 or product_data.auction_duration_hours > 720:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Auction duration must be at least 1 minute (0.017 hours) and maximum 720 hours"
                    )
                auction_duration_hours = product_data.auction_duration_hours
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auction duration is required for auction products (use auction_duration_minutes or auction_duration_hours)"
                )
            
            # For auctions, starting_price is already in Sokocoin
            sokocoin_price = product_data.starting_price
            local_price = None  # Auctions don't use local price
            currency = None
        else:
            # Regular product - validate price
            if not product_data.price or product_data.price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price is required for regular products and must be greater than 0"
                )
            
            currency = (product_data.currency or "TZS").upper()
            exchange_rate = _get_exchange_rate(currency)
            if exchange_rate <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported currency '{currency}'. Please use a supported currency."
                )
            local_price = product_data.price
            sokocoin_price = _convert_to_sokocoin(local_price, currency)
        
        # Calculate auction timing
        auction_start_time = None
        auction_end_time = None
        auction_status = "pending"  # Default status
        
        if is_auction:
            now = datetime.now(timezone.utc)
            auction_start_time = now  # Auction starts immediately
            # Use the calculated auction_duration_hours (converted from minutes if needed)
            if auction_duration_hours is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auction duration is required"
                )
            auction_end_time = now + timedelta(hours=auction_duration_hours)
            auction_status = "active"  # Start auction immediately
        
        db_product = Product(
            title=product_data.title,
            description=product_data.description,
            price=sokocoin_price,
            category=product_data.category.lower(),
            category_id=category.id,
            seller_id=current_user.id,
            image_url=product_data.image_url,
            images=product_data.images,
            unit_type=product_data.unit_type,
            stock_quantity=product_data.stock_quantity,
            is_winga_enabled=product_data.is_winga_enabled,
            has_warranty=product_data.has_warranty,
            is_private=product_data.is_private,
            is_adult_content=product_data.is_adult_content,
            tags=product_data.tags,
            local_price=local_price,
            local_currency=currency,
            # Auction fields
            is_auction=is_auction,
            starting_price=product_data.starting_price if is_auction else None,
            bid_increment=product_data.bid_increment if is_auction else None,
            auction_duration_hours=auction_duration_hours if is_auction else None,
            auction_start_time=auction_start_time,
            auction_end_time=auction_end_time,
            current_bid=product_data.starting_price if is_auction else None,
            auction_status=auction_status if is_auction else None,  # Explicitly set status
            winner_paid=False
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        # Verify auction status was set correctly
        if is_auction:
            print(f"   Auction Status: {db_product.auction_status}")
            print(f"   Auction End Time: {db_product.auction_end_time}")
            print(f"   Starting Price: {db_product.starting_price}")
            print(f"   Current Bid: {db_product.current_bid}")
        
        print("SUCCESS: Product created successfully!")
        print(f"   Product ID: {db_product.id}")
        print(f"   Is Auction: {is_auction}")
        print(f"   Stored Sokocoin Price: {db_product.price}")
        print(f"   Local Price: {db_product.local_price} {db_product.local_currency}")
        print(f"   Total products in DB: {db.query(Product).count()}")
        print(f"{'='*60}\n")
        
        # Query seller from database to get latest location_address (fresh from DB)
        seller = db.query(User).filter(User.id == current_user.id).first()
        
        # Calculate engagement for the new product
        engagement = _calculate_product_engagement(db_product, db, current_user.id)
        
        # Calculate auction time remaining if it's an auction
        time_remaining_seconds = None
        if is_auction and db_product.auction_end_time:
            now = datetime.now(timezone.utc)
            if db_product.auction_end_time.tzinfo is None:
                auction_end = db_product.auction_end_time.replace(tzinfo=timezone.utc)
            else:
                auction_end = db_product.auction_end_time
            remaining = (auction_end - now).total_seconds()
            time_remaining_seconds = max(0, int(remaining))
        
        # Get bid count if auction
        bid_count = None
        current_bidder_username = None
        if is_auction:
            bid_count = db.query(func.count(Bid.id)).filter(Bid.product_id == db_product.id).scalar() or 0
            if db_product.current_bidder_id:
                bidder = db.query(User).filter(User.id == db_product.current_bidder_id).first()
                current_bidder_username = bidder.username if bidder else None
        
        product_dict = {
            "id": db_product.id,
            "title": db_product.title,
            "description": db_product.description,
            "price": db_product.price,
            "local_price": db_product.local_price,
            "local_currency": db_product.local_currency,
            "category": db_product.category,
            "unit_type": db_product.unit_type,
            "stock_quantity": db_product.stock_quantity,
            "is_winga_enabled": db_product.is_winga_enabled,
            "has_warranty": db_product.has_warranty,
            "is_private": db_product.is_private,
            "is_adult_content": db_product.is_adult_content,
            "tags": db_product.tags if db_product.tags else [],
            "seller_id": db_product.seller_id,
            "seller_username": seller.username if seller else current_user.username,
            "seller_location": getattr(seller, "location_address", None) if seller else None,
            "seller_profile_image": seller.profile_image if seller else current_user.profile_image,
            "image_url": db_product.image_url,
            "images": db_product.images if db_product.images else [],
            "likes": engagement['likes'],
            "comments": engagement['comments'],
            "rating": engagement['rating'],
            "is_liked": engagement['is_liked'],
            "is_sponsored": db_product.is_sponsored,
            # Auction fields
            "is_auction": is_auction,
            "starting_price": db_product.starting_price,
            "bid_increment": db_product.bid_increment,
            # Convert to int if it's a whole number (for backward compatibility with int schema)
            # Otherwise keep as float for exact minutes
            "auction_duration_hours": int(db_product.auction_duration_hours) if db_product.auction_duration_hours is not None and db_product.auction_duration_hours == int(db_product.auction_duration_hours) else db_product.auction_duration_hours,
            "auction_start_time": db_product.auction_start_time,
            "auction_end_time": db_product.auction_end_time,
            "current_bid": db_product.current_bid,
            "current_bidder_id": db_product.current_bidder_id,
            "current_bidder_username": current_bidder_username,
            "auction_status": auction_status if is_auction else None,  # Use the status we set, not DB default
            "winner_id": db_product.winner_id,
            "winner_paid": db_product.winner_paid if is_auction else None,
            "bid_count": bid_count,
            "time_remaining_seconds": time_remaining_seconds,
            "created_at": db_product.created_at,
            "updated_at": db_product.updated_at,
        }
        
        return ProductResponse(**product_dict)
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR creating product: {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating product: {str(e)}"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update product (only owner can update)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user is the owner
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this product"
        )
    
    # Update fields
    update_data = product_data.dict(exclude_unset=True)
    local_price_update = update_data.pop("price", None)
    currency_update = update_data.pop("currency", None)
    
    if local_price_update is not None or currency_update is not None:
        new_currency = (currency_update or product.local_currency or "TZS").upper()
        if local_price_update is not None:
            new_local_price = local_price_update
        elif product.local_price is not None:
            new_local_price = product.local_price
        else:
            new_local_price = _convert_from_sokocoin(product.price, new_currency)
        
        product.local_price = new_local_price
        product.local_currency = new_currency
        exchange_rate = _get_exchange_rate(new_currency)
        if exchange_rate <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported currency '{new_currency}'. Please use a supported currency."
            )
        product.price = _convert_to_sokocoin(new_local_price, new_currency)
    
    # Handle auction duration conversion (minutes to hours)
    if "auction_duration_minutes" in update_data:
        minutes = update_data.pop("auction_duration_minutes")
        if minutes is not None:
            if minutes < 1 or minutes > 43200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auction duration must be between 1 and 43200 minutes (720 hours)"
                )
            update_data["auction_duration_hours"] = minutes / 60.0
    elif "auction_duration_hours" in update_data:
        hours = update_data.get("auction_duration_hours")
        if hours is not None and (hours <= 0.016 or hours > 720):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Auction duration must be at least 1 minute (0.017 hours) and maximum 720 hours"
            )
    
    for field, value in update_data.items():
        if field == "category" and value:
            # Verify category exists
            category = db.query(Category).filter(Category.slug == value.lower()).first()
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category '{value}' not found"
                )
            setattr(product, field, value.lower())
            product.category_id = category.id
        else:
            setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    seller = db.query(User).filter(User.id == product.seller_id).first()
    
    # Calculate real-time engagement stats
    engagement = _calculate_product_engagement(product, db, current_user.id)
    
    product_dict = {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "local_price": product.local_price,
        "local_currency": product.local_currency,
        "category": product.category,
        "unit_type": product.unit_type,
        "stock_quantity": product.stock_quantity,
        "is_winga_enabled": product.is_winga_enabled,
        "has_warranty": product.has_warranty,
        "is_private": product.is_private,
        "is_adult_content": product.is_adult_content,
        "tags": product.tags if product.tags else [],
        "seller_id": product.seller_id,
        "seller_username": seller.username if seller else "Unknown",
        "seller_location": getattr(seller, "location_address", None) if seller else None,
        "seller_profile_image": seller.profile_image if seller else None,
        "image_url": product.image_url if product.image_url else None,
        "images": [img for img in (product.images or []) if img] if product.images else [],
        "likes": engagement['likes'],
        "comments": engagement['comments'],
        "rating": engagement['rating'],
        "is_liked": engagement['is_liked'],
        "is_sponsored": product.is_sponsored,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }
    
    return ProductResponse(**product_dict)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: User = Depends(require_user_type(UserType.SUPPLIER, UserType.RETAILER)),
    db: Session = Depends(get_db)
):
    """Delete product (only owner can delete)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user is the owner
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this product"
        )
    
    # Delete related engagement records
    db.query(ProductLike).filter(ProductLike.product_id == product.id).delete()
    db.query(ProductComment).filter(ProductComment.product_id == product.id).delete()
    db.query(ProductRating).filter(ProductRating.product_id == product.id).delete()
    
    # Attempt to remove associated files
    _delete_product_files(product)
    
    db.delete(product)
    db.commit()
    
    return None


# Like/Unlike Product
@router.post("/{product_id}/like", status_code=status.HTTP_200_OK)
async def like_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Like a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if already liked
    existing_like = db.query(ProductLike).filter(
        ProductLike.product_id == product_id,
        ProductLike.user_id == current_user.id
    ).first()
    
    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already liked"
        )
    
    # Create like
    like = ProductLike(
        product_id=product_id,
        user_id=current_user.id
    )
    db.add(like)
    
    # Create notification for product owner (if not liking own product)
    if product.seller_id != current_user.id:
        notification = Notification(
            user_id=product.seller_id,
            notification_type="like",
            title="New Like",
            message=f"{current_user.username} liked your product '{product.title}'",
            related_user_id=current_user.id,
            related_product_id=product_id
        )
        db.add(notification)
    
    db.commit()
    
    # Calculate updated engagement
    engagement = _calculate_product_engagement(product, db, current_user.id)
    
    return {
        "message": "Product liked successfully",
        "likes": engagement['likes'],
        "is_liked": True
    }


@router.delete("/{product_id}/like", status_code=status.HTTP_200_OK)
async def unlike_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unlike a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Find and delete like
    like = db.query(ProductLike).filter(
        ProductLike.product_id == product_id,
        ProductLike.user_id == current_user.id
    ).first()
    
    if not like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product not liked"
        )
    
    db.delete(like)
    db.commit()
    
    # Calculate updated engagement
    engagement = _calculate_product_engagement(product, db, current_user.id)
    
    return {
        "message": "Product unliked successfully",
        "likes": engagement['likes'],
        "is_liked": False
    }


# Comments
@router.get("/{product_id}/comments", response_model=List[ProductCommentResponse])
async def get_product_comments(
    product_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get comments for a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    comments = db.query(ProductComment).filter(
        ProductComment.product_id == product_id
    ).order_by(desc(ProductComment.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()
        result.append(ProductCommentResponse(
            id=comment.id,
            product_id=comment.product_id,
            user_id=comment.user_id,
            username=user.username if user else "Unknown",
            user_profile_image=user.profile_image if user else None,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        ))
    
    return result


@router.post("/{product_id}/comments", response_model=ProductCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_product_comment(
    product_id: int,
    comment_data: ProductCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    comment = ProductComment(
        product_id=product_id,
        user_id=current_user.id,
        content=comment_data.content
    )
    db.add(comment)
    
    # Create notification for product owner (if not commenting on own product)
    if product.seller_id != current_user.id:
        notification = Notification(
            user_id=product.seller_id,
            notification_type="comment",
            title="New Comment",
            message=f"{current_user.username} commented on your product '{product.title}'",
            related_user_id=current_user.id,
            related_product_id=product_id
        )
        db.add(notification)
    
    db.commit()
    db.refresh(comment)
    
    return ProductCommentResponse(
        id=comment.id,
        product_id=comment.product_id,
        user_id=comment.user_id,
        username=current_user.username,
        user_profile_image=current_user.profile_image,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


# Ratings
@router.post("/{product_id}/rating", response_model=ProductRatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_product(
    product_id: int,
    rating_data: ProductRatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Rate a product (or update existing rating)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user already rated this product
    existing_rating = db.query(ProductRating).filter(
        ProductRating.product_id == product_id,
        ProductRating.user_id == current_user.id
    ).first()
    
    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating_data.rating
        db.commit()
        db.refresh(existing_rating)
        
        return ProductRatingResponse(
            id=existing_rating.id,
            product_id=existing_rating.product_id,
            user_id=existing_rating.user_id,
            username=current_user.username,
            rating=existing_rating.rating,
            created_at=existing_rating.created_at,
            updated_at=existing_rating.updated_at
        )
    else:
        # Create new rating
        rating = ProductRating(
            product_id=product_id,
            user_id=current_user.id,
            rating=rating_data.rating
        )
        db.add(rating)
        
        # Create notification for product owner (if not rating own product)
        if product.seller_id != current_user.id:
            notification = Notification(
                user_id=product.seller_id,
                notification_type="rating",
                title="New Rating",
                message=f"{current_user.username} rated your product '{product.title}' {rating_data.rating} stars",
                related_user_id=current_user.id,
                related_product_id=product_id
            )
            db.add(notification)
        
        db.commit()
        db.refresh(rating)
        
        return ProductRatingResponse(
            id=rating.id,
            product_id=rating.product_id,
            user_id=rating.user_id,
            username=current_user.username,
            rating=rating.rating,
            created_at=rating.created_at,
            updated_at=rating.updated_at
        )

