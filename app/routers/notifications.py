from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from database import get_db
from models import Notification, User, Product
from schemas import NotificationResponse
from auth import get_current_active_user

router = APIRouter()


def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    related_user_id: Optional[int] = None,
    related_product_id: Optional[int] = None,
    related_order_id: Optional[int] = None,
    related_conversation_id: Optional[int] = None,
    db: Session = None
):
    """Helper function to create a notification"""
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        related_user_id=related_user_id,
        related_product_id=related_product_id,
        related_order_id=related_order_id,
        related_conversation_id=related_conversation_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()
    
    # Convert to response format with related entity details
    result = []
    for notification in notifications:
        notification_dict = {
            "id": notification.id,
            "user_id": notification.user_id,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "is_read": notification.is_read,
            "related_user_id": notification.related_user_id,
            "related_product_id": notification.related_product_id,
            "related_order_id": notification.related_order_id,
            "related_conversation_id": notification.related_conversation_id,
            "related_user_username": None,
            "related_user_profile_image": None,
            "related_product_title": None,
            "related_product_image": None,
            "created_at": notification.created_at,
        }
        
        # Get related user info if available
        if notification.related_user_id:
            related_user = db.query(User).filter(User.id == notification.related_user_id).first()
            if related_user:
                notification_dict["related_user_username"] = related_user.username
                notification_dict["related_user_profile_image"] = related_user.profile_image
        
        # Get related product info if available
        if notification.related_product_id:
            related_product = db.query(Product).filter(Product.id == notification.related_product_id).first()
            if related_product:
                notification_dict["related_product_title"] = related_product.title
                notification_dict["related_product_image"] = related_product.image_url
        
        result.append(NotificationResponse(**notification_dict))
    
    return result


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications"""
    count = db.query(func.count(Notification.id)).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).scalar() or 0
    
    return {"unread_count": count}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    
    # Build response
    notification_dict = {
        "id": notification.id,
        "user_id": notification.user_id,
        "notification_type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "related_user_id": notification.related_user_id,
        "related_product_id": notification.related_product_id,
        "related_order_id": notification.related_order_id,
        "related_conversation_id": notification.related_conversation_id,
        "related_user_username": None,
        "related_user_profile_image": None,
        "related_product_title": None,
        "related_product_image": None,
        "created_at": notification.created_at,
    }
    
    if notification.related_user_id:
        related_user = db.query(User).filter(User.id == notification.related_user_id).first()
        if related_user:
            notification_dict["related_user_username"] = related_user.username
            notification_dict["related_user_profile_image"] = related_user.profile_image
    
    if notification.related_product_id:
        related_product = db.query(Product).filter(Product.id == notification.related_product_id).first()
        if related_product:
            notification_dict["related_product_title"] = related_product.title
            notification_dict["related_product_image"] = related_product.image_url
    
    return NotificationResponse(**notification_dict)


@router.put("/read-all", response_model=dict)
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    updated = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"updated_count": updated}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    db.delete(notification)
    db.commit()
    
    return None


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_all_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete all notifications for the current user"""
    deleted_count = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "message": f"Deleted {deleted_count} notification(s)",
        "deleted_count": deleted_count
    }
