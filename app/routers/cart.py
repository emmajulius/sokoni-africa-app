from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import CartItem, Product, User
from schemas import CartItemCreate, CartItemResponse
from auth import get_current_user, get_current_active_user, require_user_type
from models import UserType

router = APIRouter()


@router.get("", response_model=List[CartItemResponse])
async def get_cart_items(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's cart items"""
    cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    
    result = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            item_dict = {
                **item.__dict__,
                "product": product.__dict__
            }
            # Add seller info
            seller = db.query(User).filter(User.id == product.seller_id).first()
            item_dict["product"]["seller_username"] = seller.username if seller else "Unknown"
            item_dict["product"]["seller_location"] = None
            item_dict["product"]["seller_profile_image"] = seller.profile_image if seller else None
            result.append(CartItemResponse(**item_dict))
    
    return result


@router.post("", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    cart_item: CartItemCreate,
    current_user: User = Depends(require_user_type(UserType.CLIENT, UserType.RETAILER)),
    db: Session = Depends(get_db)
):
    """Add item to cart (clients and retailers only)"""
    # Check if product exists
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if item already in cart
    existing_item = db.query(CartItem).filter(
        CartItem.user_id == current_user.id,
        CartItem.product_id == cart_item.product_id
    ).first()
    
    if existing_item:
        # Update quantity
        existing_item.quantity += cart_item.quantity
        db.commit()
        db.refresh(existing_item)
        
        item_dict = {
            **existing_item.__dict__,
            "product": product.__dict__
        }
        seller = db.query(User).filter(User.id == product.seller_id).first()
        item_dict["product"]["seller_username"] = seller.username if seller else "Unknown"
        item_dict["product"]["seller_location"] = None
        item_dict["product"]["seller_profile_image"] = seller.profile_image if seller else None
        
        return CartItemResponse(**item_dict)
    
    # Create new cart item
    db_item = CartItem(
        user_id=current_user.id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    item_dict = {
        **db_item.__dict__,
        "product": product.__dict__
    }
    seller = db.query(User).filter(User.id == product.seller_id).first()
    item_dict["product"]["seller_username"] = seller.username if seller else "Unknown"
    item_dict["product"]["seller_location"] = None
    item_dict["product"]["seller_profile_image"] = seller.profile_image if seller else None
    
    return CartItemResponse(**item_dict)


@router.put("/{item_id}", response_model=Optional[CartItemResponse])
async def update_cart_item(
    item_id: int,
    quantity: int = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update cart item quantity"""
    cart_item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    if cart_item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this cart item"
        )
    
    if quantity <= 0:
        db.delete(cart_item)
        db.commit()
        return None
    
    cart_item.quantity = quantity
    db.commit()
    db.refresh(cart_item)
    
    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    item_dict = {
        **cart_item.__dict__,
        "product": product.__dict__
    }
    seller = db.query(User).filter(User.id == product.seller_id).first()
    item_dict["product"]["seller_username"] = seller.username if seller else "Unknown"
    item_dict["product"]["seller_location"] = None
    item_dict["product"]["seller_profile_image"] = seller.profile_image if seller else None
    
    return CartItemResponse(**item_dict)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove item from cart"""
    cart_item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    if cart_item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove this cart item"
        )
    
    db.delete(cart_item)
    db.commit()
    
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Clear all items from cart"""
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()
    
    return None

