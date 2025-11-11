from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from database import get_db
from models import SavedProduct, Product, User
from schemas import SavedProductCreate, SavedProductResponse, ProductResponse
from auth import get_current_active_user

router = APIRouter()


def product_to_response(product: Product, db: Session) -> ProductResponse:
    """Convert Product model to ProductResponse"""
    seller = db.query(User).filter(User.id == product.seller_id).first()
    
    # Get images
    images = []
    if product.image_url:
        images.append(product.image_url)
    if product.images:
        images.extend(product.images)
    
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
        "tags": product.tags or [],
        "seller_id": product.seller_id,
        "seller_username": seller.username if seller else "",
        "seller_location": None,  # Not stored in User model
        "seller_profile_image": seller.profile_image if seller else None,
        "image_url": product.image_url,
        "images": images,
        "likes": product.likes,
        "comments": product.comments,
        "rating": product.rating,
        "is_sponsored": product.is_sponsored,
        "created_at": product.created_at,
        "updated_at": product.updated_at
    }
    return ProductResponse(**product_dict)


@router.post("", response_model=SavedProductResponse, status_code=status.HTTP_201_CREATED)
async def save_product(
    saved_product_data: SavedProductCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Save a product for later"""
    # Validate product exists
    product = db.query(Product).filter(Product.id == saved_product_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if already saved
    existing = db.query(SavedProduct).filter(
        SavedProduct.user_id == current_user.id,
        SavedProduct.product_id == saved_product_data.product_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already saved"
        )
    
    # Create saved product
    db_saved = SavedProduct(
        user_id=current_user.id,
        product_id=saved_product_data.product_id
    )
    
    db.add(db_saved)
    db.commit()
    db.refresh(db_saved)
    
    return SavedProductResponse(
        id=db_saved.id,
        user_id=db_saved.user_id,
        product_id=db_saved.product_id,
        product=product_to_response(product, db),
        created_at=db_saved.created_at
    )


@router.get("", response_model=List[SavedProductResponse])
async def get_saved_products(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's saved products"""
    saved_products = db.query(SavedProduct).filter(
        SavedProduct.user_id == current_user.id
    ).order_by(desc(SavedProduct.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for saved in saved_products:
        product = db.query(Product).filter(Product.id == saved.product_id).first()
        if product:
            result.append(SavedProductResponse(
                id=saved.id,
                user_id=saved.user_id,
                product_id=saved.product_id,
                product=product_to_response(product, db),
                created_at=saved.created_at
            ))
    
    return result


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_product(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove a product from saved list"""
    saved_product = db.query(SavedProduct).filter(
        SavedProduct.user_id == current_user.id,
        SavedProduct.product_id == product_id
    ).first()
    
    if not saved_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in saved list"
        )
    
    db.delete(saved_product)
    db.commit()
    
    return None


@router.get("/check/{product_id}")
async def check_saved(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if a product is saved"""
    saved_product = db.query(SavedProduct).filter(
        SavedProduct.user_id == current_user.id,
        SavedProduct.product_id == product_id
    ).first()
    
    return {"is_saved": saved_product is not None}

