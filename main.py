from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response
from database import engine, get_db
from models import Base
from config import settings
from app.routers import auth, users, products, categories, stories, cart, orders, uploads, messages, reports, saved_products, kyc, notifications, wallet, auctions, admin
from security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityLoggingMiddleware
)
from pathlib import Path
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables (only if not in production or if explicitly enabled)
# In production (Render), tables should be managed via migrations, not auto-creation
if os.getenv("ENVIRONMENT", "development").lower() != "production" or os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create database tables automatically: {e}")
        print("If this is production, ensure tables are created via migrations.")

app = FastAPI(
    title="Sokoni Africa API",
    description="RESTful API for Sokoni Africa E-commerce Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if settings.DEBUG else None,  # Disable redoc in production
    openapi_url="/openapi.json" if settings.DEBUG else None,  # Disable OpenAPI schema in production
)

# CORS Middleware - Secure configuration
print(f"[CORS] ALLOWED_ORIGINS setting: {settings.ALLOWED_ORIGINS}")
print(f"[CORS] ALLOWED_ORIGIN_REGEX setting: {settings.ALLOWED_ORIGIN_REGEX}")
allowed_origins = settings.cors_origins
allow_origin_regex = settings.cors_origin_regex

# In production, restrict CORS to specific origins
if settings.ENVIRONMENT == "production" and "*" in allowed_origins:
    logger.warning("CORS is set to allow all origins in production! This is a security risk.")
    # In production, you should set specific origins in .env
    # For now, we'll keep it but log a warning

print(f"[CORS] Resolved allow_origins: {allowed_origins}")
print(f"[CORS] Resolved allow_origin_regex: {allow_origin_regex}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],  # Explicit headers
    expose_headers=["X-Process-Time"],  # Only expose necessary headers
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add security middleware (order matters - add in reverse order of execution)
# Note: Middleware order is important - they execute in reverse order
# Security headers first (innermost, executes last)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting (before headers so headers are added to rate limit responses)
app.add_middleware(RateLimitMiddleware)

# Request size limiting
app.add_middleware(RequestSizeLimitMiddleware)

# Security logging last (outermost, executes first) - reduced logging for performance
app.add_middleware(SecurityLoggingMiddleware)

# Add GZip compression for API responses (reduces data transfer)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    """
    Security middleware: Ensure /admin routes require authentication
    This runs BEFORE the route handler to catch all /admin requests
    """
    path = request.url.path
    
    # Only check /admin routes (not /admin/login or /admin/logout)
    if path == "/admin" or path == "/admin/":
        # Check for admin_token cookie
        token = request.cookies.get("admin_token")
        if not token:
            # No token - redirect to login immediately
            from fastapi.responses import RedirectResponse
            response = RedirectResponse(url="/admin/login", status_code=303)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        
        # Token exists - let the route handler verify it
        # (route handler will check if token is valid and user is admin)
    
    # Continue to next middleware/route handler
    response = await call_next(request)
    return response


@app.middleware("http")
async def add_private_network_cors_headers(request: Request, call_next):
    """
    Chrome requires the Access-Control-Allow-Private-Network header for
    fetches targeting local/private network addresses. Without it, web
    clients using Authorization headers will fail their CORS preflight
    requests with "Failed to fetch".
    Also add caching headers for API responses where appropriate.
    """
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    
    path = request.url.path
    
    # Add CORS and cache headers for images and static files (critical for admin panel)
    is_image_or_static = (
        "/uploads/" in path or 
        "/static/" in path or
        path.startswith("/api/uploads/")
    )
    
    if is_image_or_static:
        # Essential CORS headers for images to load in admin panel
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        # Cache images for better performance
        response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
        # Ensure proper content type
        if path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            if 'Content-Type' not in response.headers:
                if path.endswith('.png'):
                    response.headers["Content-Type"] = "image/png"
                elif path.endswith(('.jpg', '.jpeg')):
                    response.headers["Content-Type"] = "image/jpeg"
                elif path.endswith('.gif'):
                    response.headers["Content-Type"] = "image/gif"
                elif path.endswith('.webp'):
                    response.headers["Content-Type"] = "image/webp"
    
    # Add cache headers for GET requests to API endpoints (short cache for dynamic data)
    elif request.method == "GET" and path.startswith("/api/"):
        # Don't cache auth endpoints or user-specific data
        if not any(p in path for p in ["/auth", "/users/me", "/cart", "/orders", "/wallet"]):
            response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    
    return response

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(categories.router, prefix="/api/categories", tags=["Categories"])
app.include_router(stories.router, prefix="/api/stories", tags=["Stories"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(saved_products.router, prefix="/api/saved-products", tags=["Saved Products"])
app.include_router(kyc.router, prefix="/api/kyc", tags=["KYC"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(wallet.router, prefix="/api", tags=["Wallet"])
app.include_router(auctions.router, prefix="/api", tags=["Auctions"])

# Include admin router (no prefix, handles /admin routes)
# IMPORTANT: Admin router must be included BEFORE static mounts to ensure auth checks run first
app.include_router(admin.router)

# Mount static files for admin panel (CSS, JS)
static_dir = Path("static")
if static_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    except Exception as e:
        print(f"Warning: Could not mount static files: {e}")

# Mount static files for uploaded images (fallback)
uploads_dir = Path("uploads")
if uploads_dir.exists():
    try:
        app.mount("/api/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
    except Exception as e:
        print(f"Warning: Could not mount static files: {e}")


@app.get("/")
async def root():
    """Root endpoint - blocked for security"""
    from fastapi import HTTPException, status
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Not Found"
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

