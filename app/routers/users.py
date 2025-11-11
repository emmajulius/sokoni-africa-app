from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    User,
    Follow,
    Product,
    Order,
    OrderStatus,
    Notification,
    OrderItem,
)
from schemas import UserUpdate, UserResponse
from auth import get_current_user, get_current_active_user

router = APIRouter()


def _calculate_user_stats(user: User, db: Session) -> dict:
    """Calculate user statistics including followers, following, sold products, and rating"""
    # Count followers (users who follow this user)
    followers_count = db.query(func.count(Follow.id)).filter(
        Follow.following_id == user.id
    ).scalar() or 0
    
    # Count following (users this user follows)
    following_count = db.query(func.count(Follow.id)).filter(
        Follow.follower_id == user.id
    ).scalar() or 0
    
    # Count sold products based on delivered order items
    sold_products_count = (
        db.query(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.seller_id == user.id,
            Order.status == OrderStatus.DELIVERED,
        )
        .scalar()
        or 0
    )
    
    # Calculate average rating from completed orders
    # For now, we'll use product ratings if available, otherwise 0.0
    avg_rating = db.query(func.avg(Product.rating)).filter(
        Product.seller_id == user.id,
        Product.rating > 0
    ).scalar() or 0.0
    
    return {
        'followers_count': followers_count,
        'following_count': following_count,
        'sold_products_count': sold_products_count,
        'rating': float(avg_rating) if avg_rating else 0.0
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with statistics"""
    stats = _calculate_user_stats(current_user, db)
    
    # Create response dict
    user_dict = {
        'id': current_user.id,
        'username': current_user.username,
        'full_name': current_user.full_name,
        'email': current_user.email,
        'phone': current_user.phone,
        'user_type': current_user.user_type,
        'gender': current_user.gender,
        'profile_image': current_user.profile_image,
        'is_active': current_user.is_active,
        'is_verified': current_user.is_verified,
        'location_address': current_user.location_address,
        'latitude': current_user.latitude,
        'longitude': current_user.longitude,
        'followers_count': stats['followers_count'],
        'following_count': stats['following_count'],
        'sold_products_count': stats['sold_products_count'],
        'rating': stats['rating'],
        'created_at': current_user.created_at,
    }
    
    return UserResponse(**user_dict)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    # Check if username is being changed and if it's available
    if user_update.username and user_update.username != current_user.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username
    
    # Update other fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.gender is not None:
        current_user.gender = user_update.gender
    if user_update.profile_image is not None:
        current_user.profile_image = user_update.profile_image
    if user_update.latitude is not None:
        current_user.latitude = user_update.latitude
    if user_update.longitude is not None:
        current_user.longitude = user_update.longitude
    if user_update.location_address is not None:
        current_user.location_address = user_update.location_address
    
    db.commit()
    db.refresh(current_user)
    
    # Calculate stats and return
    stats = _calculate_user_stats(current_user, db)
    user_dict = {
        'id': current_user.id,
        'username': current_user.username,
        'full_name': current_user.full_name,
        'email': current_user.email,
        'phone': current_user.phone,
        'user_type': current_user.user_type,
        'gender': current_user.gender,
        'profile_image': current_user.profile_image,
        'is_active': current_user.is_active,
        'is_verified': current_user.is_verified,
        'location_address': current_user.location_address,
        'latitude': current_user.latitude,
        'longitude': current_user.longitude,
        'followers_count': stats['followers_count'],
        'following_count': stats['following_count'],
        'sold_products_count': stats['sold_products_count'],
        'rating': stats['rating'],
        'created_at': current_user.created_at,
    }
    
    return UserResponse(**user_dict)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID with statistics"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Calculate stats and return
    stats = _calculate_user_stats(user, db)
    user_dict = {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'email': user.email,
        'phone': user.phone,
        'user_type': user.user_type,
        'gender': user.gender,
        'profile_image': user.profile_image,
        'is_active': user.is_active,
        'is_verified': user.is_verified,
        'followers_count': stats['followers_count'],
        'following_count': stats['following_count'],
        'rating': stats['rating'],
        'created_at': user.created_at,
    }
    
    return UserResponse(**user_dict)


@router.post("/{user_id}/follow", status_code=status.HTTP_201_CREATED)
async def follow_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Follow a user"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    # Check if user exists
    user_to_follow = db.query(User).filter(User.id == user_id).first()
    if not user_to_follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already following
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()
    
    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )
    
    # Create follow relationship
    follow = Follow(
        follower_id=current_user.id,
        following_id=user_id
    )
    db.add(follow)
    
    # Create notification for the user being followed
    notification = Notification(
        user_id=user_id,
        notification_type="follow",
        title="New Follower",
        message=f"{current_user.username} started following you",
        related_user_id=current_user.id
    )
    db.add(notification)
    
    db.commit()
    db.refresh(follow)
    
    return {
        "message": "Successfully followed user",
        "followers_count": db.query(func.count(Follow.id)).filter(
            Follow.following_id == user_id
        ).scalar() or 0
    }


@router.delete("/{user_id}/follow", status_code=status.HTTP_200_OK)
async def unfollow_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unfollow a user"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unfollow yourself"
        )
    
    # Check if following
    follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()
    
    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user"
        )
    
    db.delete(follow)
    db.commit()
    
    return {
        "message": "Successfully unfollowed user",
        "followers_count": db.query(func.count(Follow.id)).filter(
            Follow.following_id == user_id
        ).scalar() or 0
    }


@router.get("/{user_id}/is-following", status_code=status.HTTP_200_OK)
async def check_if_following(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if current user is following another user"""
    if not current_user or current_user.is_guest:
        return {"is_following": False}
    
    follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()
    
    return {"is_following": follow is not None}


@router.get("/{user_id}/follows-you", status_code=status.HTTP_200_OK)
async def check_if_follows_you(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if another user follows the current user"""
    if not current_user or current_user.is_guest:
        return {"follows_you": False}
    
    follow = db.query(Follow).filter(
        Follow.follower_id == user_id,
        Follow.following_id == current_user.id
    ).first()
    
    return {"follows_you": follow is not None}


@router.get("/{user_id}/followers", status_code=status.HTTP_200_OK)
async def get_followers(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of followers for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get followers
    follows = db.query(Follow).filter(
        Follow.following_id == user_id
    ).offset(skip).limit(limit).all()
    
    result = []
    for follow in follows:
        follower = db.query(User).filter(User.id == follow.follower_id).first()
        if follower:
            # Check if current user follows this follower back
            is_following_back = False
            if current_user and not current_user.is_guest:
                follow_back = db.query(Follow).filter(
                    Follow.follower_id == current_user.id,
                    Follow.following_id == follower.id
                ).first()
                is_following_back = follow_back is not None
            
            result.append({
                "id": follower.id,
                "username": follower.username,
                "full_name": follower.full_name,
                "profile_image": follower.profile_image,
                "is_verified": follower.is_verified,
                "followed_at": follow.created_at.isoformat() if follow.created_at else None,
                "is_following_back": is_following_back,
            })
    
    return {"followers": result, "total": len(result)}


@router.get("/{user_id}/following", status_code=status.HTTP_200_OK)
async def get_following(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get list of users that a user is following"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get following
    follows = db.query(Follow).filter(
        Follow.follower_id == user_id
    ).offset(skip).limit(limit).all()
    
    result = []
    for follow in follows:
        following_user = db.query(User).filter(User.id == follow.following_id).first()
        if following_user:
            result.append({
                "id": following_user.id,
                "username": following_user.username,
                "full_name": following_user.full_name,
                "profile_image": following_user.profile_image,
                "is_verified": following_user.is_verified,
                "followed_at": follow.created_at.isoformat() if follow.created_at else None,
            })
    
    return {"following": result, "total": len(result)}

