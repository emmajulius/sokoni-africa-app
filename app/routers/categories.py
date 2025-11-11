from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Category
from schemas import CategoryCreate, CategoryResponse

router = APIRouter()


@router.get("", response_model=List[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    categories = db.query(Category).all()
    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.get("/{category_slug}", response_model=CategoryResponse)
async def get_category(category_slug: str, db: Session = Depends(get_db)):
    """Get category by slug"""
    category = db.query(Category).filter(Category.slug == category_slug).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return CategoryResponse.model_validate(category)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db)
):
    """Create a new category (admin only in production)"""
    # Check if category already exists
    existing = db.query(Category).filter(
        (Category.slug == category_data.slug) | (Category.name == category_data.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category already exists"
        )
    
    db_category = Category(
        name=category_data.name,
        slug=category_data.slug.lower(),
        description=category_data.description
    )
    
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    return CategoryResponse.model_validate(db_category)

