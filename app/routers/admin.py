from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import Optional, List, Union
from datetime import datetime, timedelta
from database import get_db
from models import (
    User, Product, Order, OrderItem, Category, Notification, Wallet, WalletTransaction, OrderStatus,
    CartItem, Bid, ProductLike, ProductComment, ProductRating, SavedProduct, ProductReport,
    AdminFeeCollection, AdminCashout, AdminCashoutStatus
)
from schemas import UserUpdate, ProductUpdate
from auth import get_current_user, verify_password, create_access_token, get_password_hash
from config import settings
import os
from pathlib import Path
from urllib.parse import urlparse

router = APIRouter()

# Templates directory
templates = Jinja2Templates(directory="templates")

# Admin credentials (in production, use environment variables or database)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change this in production!
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@sokoniafrica.com")


def is_admin_user(user: User) -> bool:
    """Check if user is an admin (by username or email)"""
    if not user:
        return False
    # Check if user is admin by username or email
    return (user.username == ADMIN_USERNAME or 
            (user.email and user.email.lower() == ADMIN_EMAIL.lower()))


async def get_admin_user(request: Request, db: Session = Depends(get_db)) -> Union[User, RedirectResponse]:
    """Get current admin user from session (can return RedirectResponse for HTML requests)"""
    token = request.cookies.get("admin_token")
    if not token:
        # Redirect to login for HTML requests
        if request.headers.get("accept", "").startswith("text/html"):
            return RedirectResponse(url="/admin/login?expired=1", status_code=303)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    from auth import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        # Redirect to login for HTML requests when token is expired/invalid
        if request.headers.get("accept", "").startswith("text/html"):
            return RedirectResponse(url="/admin/login?expired=1", status_code=303)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if isinstance(user_id, str):
        user_id = int(user_id)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user


async def get_admin_user_dependency(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current admin user from session (for dependency injection - always returns User or raises)"""
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    from auth import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if isinstance(user_id, str):
        user_id = int(user_id)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user


# Admin Login
@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    expired = request.query_params.get("expired")
    return templates.TemplateResponse(
        "admin/login.html", 
        {
            "request": request,
            "expired": expired == "1"
        }
    )


@router.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Admin login"""
    # Find user by username or email
    user = db.query(User).filter(
        or_(User.username == username, User.email == username)
    ).first()
    
    if not user:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=401
        )
    
    # Check if user is admin
    if not is_admin_user(user):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Access denied. Admin privileges required."},
            status_code=403
        )
    
    # Verify password
    if not user.hashed_password or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=401
        )
    
    # Create admin token with 24 hour expiration (matching cookie max_age)
    from datetime import timedelta
    token = create_access_token(
        data={"sub": str(user.id), "admin": True},
        expires_delta=timedelta(hours=24)
    )
    
    # Redirect to dashboard
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(key="admin_token", value=token, httponly=True, max_age=3600*24)  # 24 hours
    return response


@router.get("/admin/logout")
async def admin_logout():
    """Admin logout"""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("admin_token")
    return response


# Admin Dashboard
@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Admin dashboard - requires authentication"""
    # Check authentication first
    admin_user_result = await get_admin_user(request, db)
    
    # If redirect response, return it immediately
    if isinstance(admin_user_result, RedirectResponse):
        return admin_user_result
    
    # Otherwise, we have a valid admin user
    admin_user = admin_user_result
    # Get statistics
    total_users = db.query(func.count(User.id)).filter(User.is_guest == False).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).scalar() or 0
    
    # Recent users (last 7 days)
    recent_users = db.query(func.count(User.id)).filter(
        User.created_at >= datetime.utcnow() - timedelta(days=7),
        User.is_guest == False
    ).scalar() or 0
    
    # Recent orders (last 7 days)
    recent_orders = db.query(func.count(Order.id)).filter(
        Order.created_at >= datetime.utcnow() - timedelta(days=7)
    ).scalar() or 0
    
    # Active products (all products are considered active, or you can filter by auction status)
    # For now, we'll count all products as active
    active_products = total_products
    
    stats = {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "recent_users": recent_users,
        "recent_orders": recent_orders,
        "active_products": active_products,
    }
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "stats": stats, "admin_user": admin_user}
    )


# Users Management
@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Admin users management page"""
    per_page = 20
    offset = (page - 1) * per_page
    
    query = db.query(User).filter(User.is_guest == False)
    
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    if user_type:
        query = query.filter(User.user_type == user_type)
    
    total = query.count()
    users = query.order_by(desc(User.created_at)).offset(offset).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": users,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "search": search,
            "user_type": user_type,
            "admin_user": admin_user
        }
    )


@router.post("/admin/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Toggle user active status"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(
    request: Request,
    user_id: int,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Edit user form"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return templates.TemplateResponse(
        "admin/user_edit.html",
        {
            "request": request,
            "user": user,
            "admin_user": admin_user
        }
    )


@router.post("/admin/users/{user_id}/update")
async def update_user(
    user_id: int,
    request: Request,
    username: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    user_type: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    is_verified: Optional[str] = Form(None),
    location_address: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Update user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    errors = []
    
    # Update username if provided and different
    if username and username != user.username:
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == username, User.id != user_id).first()
        if existing_user:
            errors.append("Username already exists")
        else:
            user.username = username
    
    # Update email if provided and different
    if email is not None and email != user.email:
        # Check if email already exists
        if email:
            existing_user = db.query(User).filter(User.email == email, User.id != user_id).first()
            if existing_user:
                errors.append("Email already exists")
            else:
                user.email = email
        else:
            user.email = None
    
    # Update phone if provided and different
    if phone is not None and phone != user.phone:
        # Check if phone already exists
        if phone:
            existing_user = db.query(User).filter(User.phone == phone, User.id != user_id).first()
            if existing_user:
                errors.append("Phone number already exists")
            else:
                user.phone = phone
        else:
            user.phone = None
    
    # Update other fields
    if full_name is not None:
        user.full_name = full_name
    
    if user_type:
        try:
            from models import UserType
            user.user_type = UserType(user_type)
        except ValueError:
            errors.append("Invalid user type")
    
    if gender:
        try:
            from models import Gender
            if gender == "":
                user.gender = None
            else:
                user.gender = Gender(gender)
        except ValueError:
            errors.append("Invalid gender")
    
    if is_verified is not None:
        user.is_verified = (is_verified == "true" or is_verified == "on")
    
    if location_address is not None:
        user.location_address = location_address
    
    if latitude is not None:
        user.latitude = latitude
    
    if longitude is not None:
        user.longitude = longitude
    
    if errors:
        return templates.TemplateResponse(
            "admin/user_edit.html",
            {
                "request": request,
                "user": user,
                "admin_user": admin_user,
                "errors": errors
            },
            status_code=400
        )
    
    db.commit()
    db.refresh(user)
    
    return RedirectResponse(url=f"/admin/users?success=User {user.username} updated successfully", status_code=303)


@router.post("/admin/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    
    return RedirectResponse(url="/admin/users", status_code=303)


# Products Management
@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Admin products management page"""
    per_page = 20
    offset = (page - 1) * per_page
    
    # Use eager loading to prevent N+1 queries (much faster)
    from sqlalchemy.orm import joinedload
    query = db.query(Product).options(joinedload(Product.seller))
    
    if search:
        query = query.filter(
            or_(
                Product.title.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )
    
    if category:
        query = query.filter(Product.category == category)
    
    total = query.count()
    products = query.order_by(desc(Product.created_at)).offset(offset).limit(per_page).all()
    
    # Seller is already loaded via eager loading above, no need for additional queries
    
    # Get categories for filter
    categories = db.query(Category).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    # Get base URL for image serving
    base_url = (settings.APP_BASE_URL or "http://localhost:8000").rstrip('/')
    
    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "search": search,
            "category": category,
            "admin_user": admin_user,
            "base_url": base_url
        }
    )


# Note: Products don't have an is_active field in the database
# If you need to enable/disable products, you would need to add this field to the Product model


def _extract_upload_path(url: Optional[str]) -> Optional[Path]:
    """Extract file path from URL"""
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
    """Delete product image files"""
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
                print(f"Deleted file: {full_path}")
        except Exception as exc:
            print(f"Warning: failed to delete file {url}: {exc}")


@router.get("/admin/products/{product_id}/delete-info", response_class=HTMLResponse)
async def product_delete_info(
    request: Request,
    product_id: int,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Show product deletion information including related orders"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get order items for this product
    order_items = db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).all()
    
    # Get unique orders
    order_ids = list(set([item.order_id for item in order_items]))
    orders = db.query(Order).filter(Order.id.in_(order_ids)).all() if order_ids else []
    
    # Load order customers
    for order in orders:
        order.customer = db.query(User).filter(User.id == order.customer_id).first()
    
    # Count other related records
    cart_items_count = db.query(func.count(CartItem.id)).filter(CartItem.product_id == product_id).scalar() or 0
    bids_count = db.query(func.count(Bid.id)).filter(Bid.product_id == product_id).scalar() or 0
    likes_count = db.query(func.count(ProductLike.id)).filter(ProductLike.product_id == product_id).scalar() or 0
    comments_count = db.query(func.count(ProductComment.id)).filter(ProductComment.product_id == product_id).scalar() or 0
    ratings_count = db.query(func.count(ProductRating.id)).filter(ProductRating.product_id == product_id).scalar() or 0
    saved_count = db.query(func.count(SavedProduct.id)).filter(SavedProduct.product_id == product_id).scalar() or 0
    
    return templates.TemplateResponse(
        "admin/product_delete_info.html",
        {
            "request": request,
            "product": product,
            "orders": orders,
            "order_items": order_items,
            "cart_items_count": cart_items_count,
            "bids_count": bids_count,
            "likes_count": likes_count,
            "comments_count": comments_count,
            "ratings_count": ratings_count,
            "saved_count": saved_count,
            "admin_user": admin_user
        }
    )


@router.post("/admin/products/{product_id}/delete")
async def delete_product(
    product_id: int,
    request: Request,
    force: Optional[str] = Form(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete product and all related records"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        # Check if product is part of any orders
        order_items = db.query(OrderItem).filter(
            OrderItem.product_id == product_id
        ).all()
        order_items_count = len(order_items)
        force_delete = force == "true"
        
        if order_items_count > 0 and not force_delete:
            # Product is part of orders - redirect to info page
            return RedirectResponse(
                url=f"/admin/products/{product_id}/delete-info",
                status_code=303
            )
        
        # Delete related records (in order to avoid foreign key constraints)
        
        # 1. Delete order items if forced deletion
        if order_items_count > 0 and force_delete:
            # Get order IDs before deleting items
            order_ids = list(set([item.order_id for item in order_items]))
            # Delete order items
            db.query(OrderItem).filter(OrderItem.product_id == product_id).delete()
            print(f"Deleted {order_items_count} order items for product {product_id}")
            
            # Check if any orders are now empty and delete them
            for order_id in order_ids:
                remaining_items = db.query(func.count(OrderItem.id)).filter(
                    OrderItem.order_id == order_id
                ).scalar() or 0
                if remaining_items == 0:
                    db.query(Order).filter(Order.id == order_id).delete()
                    print(f"Deleted empty order {order_id}")
        
        # 2. Delete cart items
        cart_items_deleted = db.query(CartItem).filter(CartItem.product_id == product_id).delete()
        print(f"Deleted {cart_items_deleted} cart items for product {product_id}")
        
        # 3. Delete bids (should cascade, but being explicit)
        bids_deleted = db.query(Bid).filter(Bid.product_id == product_id).delete()
        print(f"Deleted {bids_deleted} bids for product {product_id}")
        
        # 4. Delete product likes
        likes_deleted = db.query(ProductLike).filter(ProductLike.product_id == product_id).delete()
        print(f"Deleted {likes_deleted} product likes for product {product_id}")
        
        # 5. Delete product comments
        comments_deleted = db.query(ProductComment).filter(ProductComment.product_id == product_id).delete()
        print(f"Deleted {comments_deleted} product comments for product {product_id}")
        
        # 6. Delete product ratings
        ratings_deleted = db.query(ProductRating).filter(ProductRating.product_id == product_id).delete()
        print(f"Deleted {ratings_deleted} product ratings for product {product_id}")
        
        # 7. Delete saved products
        saved_deleted = db.query(SavedProduct).filter(SavedProduct.product_id == product_id).delete()
        print(f"Deleted {saved_deleted} saved products for product {product_id}")
        
        # 8. Delete product reports
        reports_deleted = db.query(ProductReport).filter(ProductReport.product_id == product_id).delete()
        print(f"Deleted {reports_deleted} product reports for product {product_id}")
        
        # 9. Update notifications (set related_product_id to NULL or delete)
        # We'll set to NULL to keep notification history
        notifications_updated = db.query(Notification).filter(
            Notification.related_product_id == product_id
        ).update({Notification.related_product_id: None})
        print(f"Updated {notifications_updated} notifications for product {product_id}")
        
        # 10. Delete product files
        _delete_product_files(product)
        
        # 11. Delete the product itself
        db.delete(product)
        db.commit()
        
        if force_delete and order_items_count > 0:
            print(f"Successfully force deleted product {product_id} (removed {order_items_count} order items)")
            return RedirectResponse(
                url=f"/admin/products?success=Product deleted successfully (removed {order_items_count} order item(s)).",
                status_code=303
            )
        else:
            print(f"Successfully deleted product {product_id}")
            return RedirectResponse(url="/admin/products?success=Product deleted successfully", status_code=303)
        
    except Exception as e:
        db.rollback()
        print(f"Error deleting product {product_id}: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(
            url=f"/admin/products?error=Failed to delete product: {str(e)}",
            status_code=303
        )


# Orders Management
@router.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(
    request: Request,
    page: int = Query(1, ge=1),
    status_filter: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Admin orders management page"""
    try:
        per_page = 20
        offset = (page - 1) * per_page
        
        query = db.query(Order)
        
        # Filter by status if provided
        if status_filter:
            try:
                # Convert string to OrderStatus enum
                status_enum = OrderStatus(status_filter)
                query = query.filter(Order.status == status_enum)
            except ValueError:
                # Invalid status filter, ignore it
                pass
        
        total = query.count()
        orders = query.order_by(desc(Order.created_at)).offset(offset).limit(per_page).all()
        
        # Load order items and relationships for each order
        for order in orders:
            try:
                # Load order items
                order.items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                # Load product for each order item
                for item in order.items:
                    if item.product_id:
                        item.product = db.query(Product).filter(Product.id == item.product_id).first()
                # Load customer
                if order.customer_id:
                    order.customer_obj = db.query(User).filter(User.id == order.customer_id).first()
                # Load seller
                if order.seller_id:
                    order.seller_obj = db.query(User).filter(User.id == order.seller_id).first()
            except Exception as e:
                print(f"Error loading order {order.id} relationships: {e}")
                # Set defaults to avoid template errors
                if not hasattr(order, 'items'):
                    order.items = []
                if not hasattr(order, 'customer_obj'):
                    order.customer_obj = None
                if not hasattr(order, 'seller_obj'):
                    order.seller_obj = None
        
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    except Exception as e:
        print(f"Error in admin_orders: {e}")
        import traceback
        traceback.print_exc()
        # Return empty result on error
        orders = []
        total = 0
        total_pages = 1
    
    return templates.TemplateResponse(
        "admin/orders.html",
        {
            "request": request,
            "orders": orders,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "status_filter": status_filter,
            "admin_user": admin_user
        }
    )


@router.get("/admin/orders/{order_id}", response_class=HTMLResponse)
async def view_order_details(
    request: Request,
    order_id: int,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """View order details"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Load order items with products
    order.items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in order.items:
        if item.product_id:
            item.product = db.query(Product).filter(Product.id == item.product_id).first()
    
    # Load customer
    if order.customer_id:
        order.customer_obj = db.query(User).filter(User.id == order.customer_id).first()
    
    # Load seller
    if order.seller_id:
        order.seller_obj = db.query(User).filter(User.id == order.seller_id).first()
    
    return templates.TemplateResponse(
        "admin/order_details.html",
        {
            "request": request,
            "order": order,
            "admin_user": admin_user
        }
    )


@router.post("/admin/orders/{order_id}/update-status")
async def update_order_status(
    order_id: int,
    new_status: str = Form(...),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Update order status"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    try:
        order.status = OrderStatus(new_status)
        db.commit()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    return RedirectResponse(url="/admin/orders", status_code=303)


# Admin Fees Management
@router.get("/admin/fees", response_class=HTMLResponse)
async def admin_fees_dashboard(
    request: Request,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Admin fees dashboard showing collected fees"""
    # Calculate total fees from all orders
    total_processing_fees = db.query(func.coalesce(func.sum(Order.processing_fee), 0)).scalar() or 0.0
    total_shipping_fees = db.query(func.coalesce(func.sum(Order.shipping_fee), 0)).scalar() or 0.0
    total_fees = total_processing_fees + total_shipping_fees
    
    # Calculate fees already cashed out (only COMPLETED cashouts deduct from balance, like mobile app)
    total_cashed_out = db.query(func.coalesce(func.sum(AdminCashout.amount), 0)).filter(
        AdminCashout.status == AdminCashoutStatus.COMPLETED
    ).scalar() or 0.0
    
    # Calculate pending cashouts (reserved but not yet deducted)
    pending_cashouts_amount = db.query(func.coalesce(func.sum(AdminCashout.amount), 0)).filter(
        AdminCashout.status == AdminCashoutStatus.PENDING
    ).scalar() or 0.0
    
    # Available balance = total fees - completed cashouts - pending cashouts (reserved)
    available_balance = total_fees - total_cashed_out - pending_cashouts_amount
    
    # Get pending cashouts
    pending_cashouts = db.query(AdminCashout).filter(
        AdminCashout.status == AdminCashoutStatus.PENDING
    ).order_by(desc(AdminCashout.created_at)).all()
    
    # Get recent fee collections (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_fees = db.query(
        func.coalesce(func.sum(Order.processing_fee), 0).label('processing'),
        func.coalesce(func.sum(Order.shipping_fee), 0).label('shipping')
    ).filter(Order.created_at >= thirty_days_ago).first()
    
    recent_processing = recent_fees.processing if recent_fees else 0.0
    recent_shipping = recent_fees.shipping if recent_fees else 0.0
    recent_total = recent_processing + recent_shipping
    
    # Get total orders count
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    
    stats = {
        "total_processing_fees": round(total_processing_fees, 2),
        "total_shipping_fees": round(total_shipping_fees, 2),
        "total_fees": round(total_fees, 2),
        "total_cashed_out": round(total_cashed_out, 2),  # Only COMPLETED cashouts
        "pending_cashouts_amount": round(pending_cashouts_amount, 2),  # Reserved but not deducted
        "available_balance": round(available_balance, 2),
        "recent_processing": round(recent_processing, 2),
        "recent_shipping": round(recent_shipping, 2),
        "recent_total": round(recent_total, 2),
        "total_orders": total_orders,
        "pending_cashouts_count": len(pending_cashouts),
        "pending_cashouts": pending_cashouts
    }
    
    return templates.TemplateResponse(
        "admin/fees_dashboard.html",
        {
            "request": request,
            "stats": stats,
            "admin_user": admin_user
        }
    )


@router.get("/admin/fees/cashout", response_class=HTMLResponse)
async def admin_cashout_form(
    request: Request,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Admin cashout form"""
    # Calculate available balance (only COMPLETED cashouts deduct, like mobile app)
    total_fees = (db.query(func.coalesce(func.sum(Order.processing_fee), 0)).scalar() or 0.0) + \
                 (db.query(func.coalesce(func.sum(Order.shipping_fee), 0)).scalar() or 0.0)
    total_cashed_out = db.query(func.coalesce(func.sum(AdminCashout.amount), 0)).filter(
        AdminCashout.status == AdminCashoutStatus.COMPLETED
    ).scalar() or 0.0
    pending_cashouts_amount = db.query(func.coalesce(func.sum(AdminCashout.amount), 0)).filter(
        AdminCashout.status == AdminCashoutStatus.PENDING
    ).scalar() or 0.0
    available_balance = total_fees - total_cashed_out - pending_cashouts_amount
    
    return templates.TemplateResponse(
        "admin/cashout_form.html",
        {
            "request": request,
            "available_balance": round(available_balance, 2),
            "admin_user": admin_user
        }
    )


@router.post("/admin/fees/cashout")
async def submit_admin_cashout(
    request: Request,
    amount: float = Form(...),
    currency: Optional[str] = Form(None),
    payout_method: str = Form(...),
    payout_account: Optional[str] = Form(None),
    payout_account_name: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    bank_account_number: Optional[str] = Form(None),
    bank_account_holder: Optional[str] = Form(None),
    bank_branch: Optional[str] = Form(None),
    bank_swift_code: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Submit admin cashout request"""
    # Calculate available balance (only COMPLETED cashouts deduct, like mobile app)
    total_fees = (db.query(func.coalesce(func.sum(Order.processing_fee), 0)).scalar() or 0.0) + \
                 (db.query(func.coalesce(func.sum(Order.shipping_fee), 0)).scalar() or 0.0)
    total_cashed_out = db.query(func.coalesce(func.sum(AdminCashout.amount), 0)).filter(
        AdminCashout.status == AdminCashoutStatus.COMPLETED
    ).scalar() or 0.0
    pending_cashouts_amount = db.query(func.coalesce(func.sum(AdminCashout.amount), 0)).filter(
        AdminCashout.status == AdminCashoutStatus.PENDING
    ).scalar() or 0.0
    available_balance = total_fees - total_cashed_out - pending_cashouts_amount
    
    # Validate amount
    if amount <= 0:
        return templates.TemplateResponse(
            "admin/cashout_form.html",
            {
                "request": request,
                "available_balance": round(available_balance, 2),
                "admin_user": admin_user,
                "error": "Amount must be greater than 0"
            },
            status_code=400
        )
    
    if amount > available_balance:
        return templates.TemplateResponse(
            "admin/cashout_form.html",
            {
                "request": request,
                "available_balance": round(available_balance, 2),
                "admin_user": admin_user,
                "error": f"Amount cannot exceed available balance of {available_balance:.2f} SOK"
            },
            status_code=400
        )
    
    # Validation helper functions
    import re
    
    def validate_phone_number(phone: str) -> bool:
        """Validate Tanzanian phone number format: 10 digits starting with 07/06 or +255 followed by 9 digits"""
        if not phone:
            return False
        cleaned = re.sub(r'[\s-]', '', phone)
        # Tanzanian format: +255 followed by 9 digits (total 13) OR 10 digits starting with 07 or 06
        return bool(re.match(r'^(\+255[0-9]{9}|0[67][0-9]{8})$', cleaned))
    
    def validate_bank_account_number(account: str) -> bool:
        """Validate bank account number (8-20 alphanumeric)"""
        if not account:
            return False
        return bool(re.match(r'^[0-9A-Za-z]{8,20}$', account))
    
    def validate_name(name: str) -> bool:
        """Validate name (2-100 characters, letters, spaces, hyphens, apostrophes)"""
        if not name:
            return False
        return bool(re.match(r'^[a-zA-Z\s\'-]{2,100}$', name))
    
    def validate_bank_name(name: str) -> bool:
        """Validate bank name (2-100 characters, alphanumeric and common punctuation)"""
        if not name:
            return False
        return bool(re.match(r'^[a-zA-Z0-9\s&.,\'-]{2,100}$', name))
    
    def validate_swift_code(swift: str) -> bool:
        """Validate SWIFT code (8 or 11 uppercase letters)"""
        if not swift:
            return False
        return bool(re.match(r'^[A-Z]{8}([A-Z]{3})?$', swift))
    
    # Validate payout method and required fields
    if payout_method == "mobile_money":
        if not payout_account:
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Phone number is required for mobile money"
                },
                status_code=400
            )
        # Validate phone number format
        if not validate_phone_number(payout_account):
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Invalid phone number format. Please enter a valid Tanzanian phone number: 10 digits starting with 07 or 06 (e.g., 0712345678) or with country code +255 (e.g., +255712345678)"
                },
                status_code=400
            )
        # Validate account holder name if provided
        if payout_account_name and not validate_name(payout_account_name):
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Invalid account holder name. Must be 2-100 characters and contain only letters, spaces, hyphens, and apostrophes"
                },
                status_code=400
            )
    elif payout_method == "bank_transfer":
        if not bank_name or not bank_account_number or not bank_account_holder:
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Bank name, account number, and account holder name are required for bank transfer"
                },
                status_code=400
            )
        # Validate bank name
        if not validate_bank_name(bank_name):
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Invalid bank name. Must be 2-100 characters"
                },
                status_code=400
            )
        # Validate bank account number
        if not validate_bank_account_number(bank_account_number):
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Invalid bank account number. Must be 8-20 alphanumeric characters"
                },
                status_code=400
            )
        # Validate account holder name
        if not validate_name(bank_account_holder):
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Invalid account holder name. Must be 2-100 characters and contain only letters, spaces, hyphens, and apostrophes"
                },
                status_code=400
            )
        # Validate bank branch if provided
        if bank_branch and not validate_bank_name(bank_branch):
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Invalid bank branch. Must be 2-100 characters"
                },
                status_code=400
            )
        # Validate SWIFT code if provided
        if bank_swift_code and not validate_swift_code(bank_swift_code.upper()):
            return templates.TemplateResponse(
                "admin/cashout_form.html",
                {
                    "request": request,
                    "available_balance": round(available_balance, 2),
                    "admin_user": admin_user,
                    "error": "Invalid SWIFT code. Must be 8 or 11 uppercase letters"
                },
                status_code=400
            )
        # For bank transfer, use bank_account_number as payout_account
        payout_account = bank_account_number
        if not payout_account_name:
            payout_account_name = bank_account_holder
    else:
        return templates.TemplateResponse(
            "admin/cashout_form.html",
            {
                "request": request,
                "available_balance": round(available_balance, 2),
                "admin_user": admin_user,
                "error": "Invalid payout method. Only mobile_money and bank_transfer are allowed."
            },
            status_code=400
        )
    
    # Calculate local currency amount if currency is provided
    local_currency_amount = None
    exchange_rate = None
    if currency:
        # Import exchange rate function from wallet router
        from app.routers.wallet import _get_exchange_rate, _convert_from_sokocoin
        exchange_rate = _get_exchange_rate(currency)
        local_currency_amount = _convert_from_sokocoin(amount, currency)
    
    # Create cashout request
    cashout = AdminCashout(
        amount=amount,
        currency=currency,
        local_currency_amount=local_currency_amount,
        exchange_rate=exchange_rate,
        payout_method=payout_method,
        payout_account=payout_account,
        payout_account_name=payout_account_name,
        bank_name=bank_name,
        bank_account_number=bank_account_number,
        bank_account_holder=bank_account_holder,
        bank_branch=bank_branch,
        bank_swift_code=bank_swift_code.upper() if bank_swift_code else None,
        notes=notes,
        status=AdminCashoutStatus.PENDING
    )
    db.add(cashout)
    db.commit()
    db.refresh(cashout)
    
    return RedirectResponse(url="/admin/fees/history?success=Cashout request submitted successfully", status_code=303)


@router.get("/admin/fees/history", response_class=HTMLResponse)
async def admin_cashout_history(
    request: Request,
    page: int = Query(1, ge=1),
    status_filter: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Admin cashout history"""
    per_page = 20
    offset = (page - 1) * per_page
    
    query = db.query(AdminCashout)
    
    if status_filter:
        try:
            status_enum = AdminCashoutStatus(status_filter)
            query = query.filter(AdminCashout.status == status_enum)
        except ValueError:
            pass
    
    total = query.count()
    cashouts = query.order_by(desc(AdminCashout.created_at)).offset(offset).limit(per_page).all()
    
    # Load processor for each cashout
    for cashout in cashouts:
        if cashout.processed_by:
            cashout.processor_obj = db.query(User).filter(User.id == cashout.processed_by).first()
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return templates.TemplateResponse(
        "admin/cashout_history.html",
        {
            "request": request,
            "cashouts": cashouts,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "status_filter": status_filter,
            "admin_user": admin_user
        }
    )


@router.get("/admin/fees/cashout/{cashout_id}/details")
async def get_cashout_details(
    cashout_id: int,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Get cashout details as JSON"""
    cashout = db.query(AdminCashout).filter(AdminCashout.id == cashout_id).first()
    if not cashout:
        raise HTTPException(status_code=404, detail="Cashout not found")
    
    # Load processor if exists
    processor_obj = None
    if cashout.processed_by:
        processor_obj = db.query(User).filter(User.id == cashout.processed_by).first()
    
    return JSONResponse({
        "id": cashout.id,
        "amount": cashout.amount,
        "currency": cashout.currency,
        "local_currency_amount": cashout.local_currency_amount,
        "exchange_rate": cashout.exchange_rate,
        "payout_method": cashout.payout_method,
        "payout_account": cashout.payout_account,
        "payout_account_name": cashout.payout_account_name,
        "bank_name": cashout.bank_name,
        "bank_account_number": cashout.bank_account_number,
        "bank_account_holder": cashout.bank_account_holder,
        "bank_branch": cashout.bank_branch,
        "bank_swift_code": cashout.bank_swift_code,
        "status": cashout.status.value,
        "notes": cashout.notes,
        "rejection_reason": cashout.rejection_reason,
        "created_at": cashout.created_at.strftime('%Y-%m-%d %H:%M:%S') if cashout.created_at else None,
        "processed_at": cashout.processed_at.strftime('%Y-%m-%d %H:%M:%S') if cashout.processed_at else None,
        "processor": processor_obj.username if processor_obj else None
    })


@router.post("/admin/fees/cashout/{cashout_id}/update-status")
async def update_cashout_status(
    cashout_id: int,
    new_status: str = Form(...),
    currency: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Update cashout status"""
    cashout = db.query(AdminCashout).filter(AdminCashout.id == cashout_id).first()
    if not cashout:
        raise HTTPException(status_code=404, detail="Cashout not found")
    
    try:
        old_status = cashout.status
        cashout.status = AdminCashoutStatus(new_status)
        
        # When completing, currency is required
        if new_status == AdminCashoutStatus.COMPLETED:
            if not currency:
                raise HTTPException(
                    status_code=400, 
                    detail="Currency is required when completing a cashout. Please select the currency you want to receive."
                )
            from app.routers.wallet import _get_exchange_rate, _convert_from_sokocoin
            cashout.currency = currency
            cashout.exchange_rate = _get_exchange_rate(currency)
            cashout.local_currency_amount = _convert_from_sokocoin(cashout.amount, currency)
        elif currency and not cashout.currency:
            # Allow setting currency even if not completing yet
            from app.routers.wallet import _get_exchange_rate, _convert_from_sokocoin
            cashout.currency = currency
            cashout.exchange_rate = _get_exchange_rate(currency)
            cashout.local_currency_amount = _convert_from_sokocoin(cashout.amount, currency)
        
        if notes:
            cashout.notes = notes
        if new_status in [AdminCashoutStatus.APPROVED, AdminCashoutStatus.PROCESSING, AdminCashoutStatus.COMPLETED, AdminCashoutStatus.REJECTED]:
            cashout.processed_by = admin_user.id
            cashout.processed_at = datetime.utcnow()
        db.commit()
        
        # Show success message when marking as completed
        if new_status == AdminCashoutStatus.COMPLETED:
            # Build success message with cashout details for popup
            success_params = {
                "success": "1",
                "cashout_id": str(cashout_id),
                "amount": str(cashout.amount),
                "currency": cashout.currency or "",
                "local_amount": str(cashout.local_currency_amount) if cashout.local_currency_amount else "",
                "payout_method": cashout.payout_method,
                "payout_account": cashout.payout_account
            }
            # Build query string with URL encoding
            from urllib.parse import urlencode
            query_string = urlencode({k: v for k, v in success_params.items() if v})
            return RedirectResponse(
                url=f"/admin/fees/history?{query_string}",
                status_code=303
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    return RedirectResponse(url="/admin/fees/history", status_code=303)


@router.post("/admin/fees/cashout/{cashout_id}/delete")
async def delete_cashout(
    cashout_id: int,
    admin_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db)
):
    """Delete a cashout transaction"""
    cashout = db.query(AdminCashout).filter(AdminCashout.id == cashout_id).first()
    if not cashout:
        return RedirectResponse(
            url="/admin/fees/history?error=Cashout not found",
            status_code=303
        )
    
    # Store status for warning message
    status = cashout.status.value
    amount = cashout.amount
    
    # Delete the cashout
    db.delete(cashout)
    db.commit()
    
    # Show success message
    return RedirectResponse(
        url=f"/admin/fees/history?success=Cashout #{cashout_id} (Status: {status}, Amount: {amount:.2f} SOK) has been deleted successfully",
        status_code=303
    )

