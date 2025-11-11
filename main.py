from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.requests import Request
from database import engine, get_db
from models import Base
from config import settings
from app.routers import auth, users, products, categories, stories, cart, orders, uploads, messages, reports, saved_products, kyc, notifications, wallet, auctions, admin
from pathlib import Path

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sokoni Africa API",
    description="RESTful API for Sokoni Africa E-commerce Platform",
    version="1.0.0"
)

# CORS Middleware
print(f"[CORS] ALLOWED_ORIGINS setting: {settings.ALLOWED_ORIGINS}")
print(f"[CORS] ALLOWED_ORIGIN_REGEX setting: {settings.ALLOWED_ORIGIN_REGEX}")
allowed_origins = settings.cors_origins
allow_origin_regex = settings.cors_origin_regex
print(f"[CORS] Resolved allow_origins: {allowed_origins}")
print(f"[CORS] Resolved allow_origin_regex: {allow_origin_regex}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_private_network_cors_headers(request: Request, call_next):
    """
    Chrome requires the Access-Control-Allow-Private-Network header for
    fetches targeting local/private network addresses. Without it, web
    clients using Authorization headers will fail their CORS preflight
    requests with "Failed to fetch".
    """
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
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

