from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from database import get_db
from models import ProductReport, Product, User
from schemas import ProductReportCreate, ProductReportResponse
from auth import get_current_active_user

router = APIRouter()


@router.post("", response_model=ProductReportResponse, status_code=status.HTTP_201_CREATED)
async def report_product(
    report_data: ProductReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Report a product"""
    # Validate product exists
    product = db.query(Product).filter(Product.id == report_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user already reported this product
    existing_report = db.query(ProductReport).filter(
        ProductReport.product_id == report_data.product_id,
        ProductReport.reporter_id == current_user.id
    ).first()
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reported this product"
        )
    
    # Validate reason
    valid_reasons = ["spam", "inappropriate", "fake", "other"]
    if report_data.reason not in valid_reasons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"
        )
    
    # Create report
    db_report = ProductReport(
        product_id=report_data.product_id,
        reporter_id=current_user.id,
        reason=report_data.reason,
        description=report_data.description
    )
    
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return ProductReportResponse(
        id=db_report.id,
        product_id=db_report.product_id,
        reporter_id=db_report.reporter_id,
        reason=db_report.reason,
        description=db_report.description,
        status=db_report.status,
        created_at=db_report.created_at
    )


@router.get("/my-reports", response_model=List[ProductReportResponse])
async def get_my_reports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's reports"""
    reports = db.query(ProductReport).filter(
        ProductReport.reporter_id == current_user.id
    ).order_by(desc(ProductReport.created_at)).all()
    
    return [ProductReportResponse(
        id=report.id,
        product_id=report.product_id,
        reporter_id=report.reporter_id,
        reason=report.reason,
        description=report.description,
        status=report.status,
        created_at=report.created_at
    ) for report in reports]


@router.get("/product/{product_id}", response_model=List[ProductReportResponse])
async def get_product_reports(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all reports for a product (admin only or product owner)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Only product owner can see reports
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view reports for this product"
        )
    
    reports = db.query(ProductReport).filter(
        ProductReport.product_id == product_id
    ).order_by(desc(ProductReport.created_at)).all()
    
    return [ProductReportResponse(
        id=report.id,
        product_id=report.product_id,
        reporter_id=report.reporter_id,
        reason=report.reason,
        description=report.description,
        status=report.status,
        created_at=report.created_at
    ) for report in reports]

