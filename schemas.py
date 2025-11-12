from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from models import UserType, Gender, OrderStatus, WalletTransactionType, WalletTransactionStatus


# User Schemas
class UserBase(BaseModel):
    username: str
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    user_type: UserType = UserType.CLIENT
    gender: Optional[Gender] = None


class UserCreate(UserBase):
    password: Optional[str] = None
    google_id: Optional[str] = None


class UserLogin(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    google_token: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    profile_image: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_address: Optional[str] = None


class UserResponse(UserBase):
    id: int
    profile_image: Optional[str] = None
    is_active: bool
    is_verified: bool
    followers_count: int = 0  # Number of followers
    following_count: int = 0  # Number of users being followed
    sold_products_count: int = 0  # Number of products sold
    rating: float = 0.0  # Average rating
    created_at: datetime
    
    class Config:
        from_attributes = True


# Product Schemas
class ProductBase(BaseModel):
    title: str
    description: str
    category: str
    unit_type: Optional[str] = None
    stock_quantity: Optional[int] = None
    is_winga_enabled: bool = False
    has_warranty: bool = False
    is_private: bool = False
    is_adult_content: bool = False
    tags: List[str] = []


class ProductCreate(ProductBase):
    price: Optional[float] = Field(None, description="Price in seller's local currency (required for regular products)")
    currency: str = Field(default="TZS", description="Currency code for the local price (TZS, KES, NGN, etc.)")
    image_url: Optional[str] = None
    images: List[str] = []
    # Auction fields
    is_auction: bool = Field(default=False, description="Whether this is an auction product")
    starting_price: Optional[float] = Field(None, description="Starting bid price in Sokocoin (required for auctions)")
    bid_increment: Optional[float] = Field(None, description="Minimum bid increment in Sokocoin (required for auctions)")
    auction_duration_minutes: Optional[int] = Field(None, description="Auction duration in minutes (minimum 1 minute, maximum 43200 minutes = 720 hours, required for auctions)")
    auction_duration_hours: Optional[float] = Field(None, description="Auction duration in hours (deprecated, use auction_duration_minutes instead)")


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0, description="Price in seller's local currency")
    currency: Optional[str] = Field(None, description="Currency code for the local price")
    category: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    unit_type: Optional[str] = None
    stock_quantity: Optional[int] = None
    is_winga_enabled: Optional[bool] = None
    has_warranty: Optional[bool] = None
    is_private: Optional[bool] = None
    is_adult_content: Optional[bool] = None
    tags: Optional[List[str]] = None
    # Auction fields
    auction_duration_minutes: Optional[int] = Field(None, description="Auction duration in minutes (minimum 1 minute, maximum 43200 minutes = 720 hours)")
    auction_duration_hours: Optional[float] = Field(None, description="Auction duration in hours (deprecated, use auction_duration_minutes instead)")


class ProductResponse(ProductBase):
    id: int
    price: float  # Sokocoin price (or starting price for auctions)
    local_price: Optional[float] = None
    local_currency: Optional[str] = None
    seller_id: int
    seller_username: str
    seller_location: Optional[str] = None
    seller_profile_image: Optional[str] = None
    image_url: Optional[str] = None
    images: List[str]
    likes: int
    comments: int
    rating: float
    distance: Optional[float] = None  # Distance in kilometers from user's location
    is_liked: Optional[bool] = False  # Whether the current user has liked this product
    is_sponsored: bool
    # Auction fields
    is_auction: bool = False
    starting_price: Optional[float] = None
    bid_increment: Optional[float] = None
    auction_duration_hours: Optional[float] = None  # Changed to float to support exact minutes (e.g., 8 min = 0.133 hours)
    auction_start_time: Optional[datetime] = None
    auction_end_time: Optional[datetime] = None
    current_bid: Optional[float] = None
    current_bidder_id: Optional[int] = None
    current_bidder_username: Optional[str] = None
    auction_status: Optional[str] = None  # pending, active, ended, cancelled
    winner_id: Optional[int] = None
    winner_paid: Optional[bool] = None
    bid_count: Optional[int] = None  # Total number of bids
    time_remaining_seconds: Optional[int] = None  # Time remaining until auction ends
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Bid Schemas
class BidCreate(BaseModel):
    bid_amount: float = Field(..., gt=0, description="Bid amount in Sokocoin")


class BidResponse(BaseModel):
    id: int
    product_id: int
    bidder_id: int
    bidder_username: str
    bidder_profile_image: Optional[str] = None
    bid_amount: float
    bid_time: datetime
    is_winning_bid: bool
    is_outbid: bool
    
    class Config:
        from_attributes = True


# Auction Schemas
class AuctionCreate(BaseModel):
    starting_price: float = Field(..., gt=0, description="Starting bid price in Sokocoin")
    bid_increment: float = Field(..., gt=0, description="Minimum bid increment in Sokocoin")
    auction_duration_hours: float = Field(..., gt=0.016, le=720, description="Auction duration in hours (minimum 0.017 hours = 1 minute, maximum 720 hours)")


class AuctionResponse(BaseModel):
    product_id: int
    product_title: str
    product_image: Optional[str] = None
    starting_price: float
    current_bid: Optional[float] = None
    bid_increment: float
    auction_start_time: datetime
    auction_end_time: datetime
    auction_status: str
    time_remaining_seconds: int
    bid_count: int
    current_bidder_id: Optional[int] = None
    current_bidder_username: Optional[str] = None
    winner_id: Optional[int] = None
    winner_username: Optional[str] = None
    
    class Config:
        from_attributes = True


# Category Schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    slug: str


class CategoryResponse(CategoryBase):
    id: int
    slug: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Story Schemas
class StoryBase(BaseModel):
    media_url: str
    media_type: str
    caption: Optional[str] = None


class StoryCreate(StoryBase):
    pass


class StoryResponse(StoryBase):
    id: int
    user_id: int
    username: Optional[str] = None
    user_profile_image: Optional[str] = None
    expires_at: datetime
    views_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Cart Schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemCreate(CartItemBase):
    pass


class CartItemResponse(CartItemBase):
    id: int
    user_id: int
    product: ProductResponse
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Order Schemas
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    product: ProductResponse
    
    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    shipping_address: str
    payment_method: Optional[str] = None


class OrderCreate(OrderBase):
    items: Optional[List[OrderItemCreate]] = None
    include_shipping: bool = False


class OrderResponse(OrderBase):
    id: int
    customer_id: int
    seller_id: int
    customer_username: Optional[str] = None
    customer_full_name: Optional[str] = None
    customer_profile_image: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    status: OrderStatus
    total_amount: float
    processing_fee: float = 0.0
    shipping_fee: float = 0.0
    shipping_distance_km: Optional[float] = None
    includes_shipping: bool = False
    payment_status: str
    items: List[OrderItemResponse]
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[int] = None


# OTP Schemas
class OTPSendRequest(BaseModel):
    phone: str = Field(..., description="Phone number to send OTP to")


class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., description="Phone number")
    code: str = Field(..., min_length=4, max_length=6, description="OTP code to verify")


class OTPSendResponse(BaseModel):
    success: bool
    message: str
    expires_in_minutes: int = 10


class OTPVerifyResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None  # Token for registration completion
    user: Optional[UserResponse] = None  # User data if verification successful


# Message Schemas
class MessageCreate(BaseModel):
    content: str
    conversation_id: Optional[int] = None  # If None, create new conversation
    recipient_id: Optional[int] = None  # Required if creating new conversation


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_username: str
    content: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    user1_username: str
    user2_username: str
    user1_profile_image: Optional[str] = None
    user2_profile_image: Optional[str] = None
    last_message: Optional[MessageResponse] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


# Product Report Schemas
class ProductReportCreate(BaseModel):
    product_id: int
    reason: str = Field(..., description="Report reason: spam, inappropriate, fake, other")
    description: Optional[str] = None


class ProductReportResponse(BaseModel):
    id: int
    product_id: int
    reporter_id: int
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Saved Product Schemas
class SavedProductCreate(BaseModel):
    product_id: int


class SavedProductResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    product: ProductResponse
    created_at: datetime
    
    class Config:
        from_attributes = True


# KYC Document Schemas
class KYCDocumentCreate(BaseModel):
    document_type: str = Field(..., description="Type of document: id_card, passport, driver_license, etc.")
    document_url: str = Field(..., description="URL of the uploaded document")


class KYCDocumentResponse(BaseModel):
    id: int
    user_id: int
    document_type: str
    document_url: str
    status: str
    rejection_reason: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class KYCVerificationStatus(BaseModel):
    is_verified: bool
    has_document: bool
    document_status: Optional[str] = None
    documents: List[KYCDocumentResponse] = []


# Product Comment Schemas
class ProductCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")


class ProductCommentResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    username: str
    user_profile_image: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Product Rating Schemas
class ProductRatingCreate(BaseModel):
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")


class ProductRatingResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    username: str
    rating: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    related_user_id: Optional[int] = None
    related_product_id: Optional[int] = None
    related_order_id: Optional[int] = None
    related_conversation_id: Optional[int] = None
    related_user_username: Optional[str] = None
    related_user_profile_image: Optional[str] = None
    related_product_title: Optional[str] = None
    related_product_image: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Wallet Schemas
class WalletResponse(BaseModel):
    id: int
    user_id: int
    sokocoin_balance: float
    total_earned: float
    total_spent: float
    total_topup: float
    total_cashout: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WalletTransactionResponse(BaseModel):
    id: int
    wallet_id: int
    user_id: int
    transaction_type: WalletTransactionType
    status: WalletTransactionStatus
    sokocoin_amount: float
    local_currency_amount: Optional[float] = None
    local_currency_code: Optional[str] = None
    exchange_rate: Optional[float] = None
    payment_gateway: Optional[str] = None
    payment_reference: Optional[str] = None
    gateway_transaction_id: Optional[str] = None
    payout_method: Optional[str] = None
    payout_account: Optional[str] = None
    payout_reference: Optional[str] = None
    description: Optional[str] = None
    extra_data: Optional[dict] = None  # Additional data (renamed from metadata)
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TopupCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in local currency")
    currency: str = Field(default="TZS", description="Currency code (TZS, KES, NGN, etc.)")
    payment_method: str = Field(default="card", description="Payment method: card, mobile_money, bank_transfer")
    phone_number: Optional[str] = None  # For mobile money
    email: Optional[str] = None
    full_name: Optional[str] = None


class CashoutCreate(BaseModel):
    sokocoin_amount: float = Field(..., gt=0, description="Amount in Sokocoin to cashout")
    payout_method: str = Field(..., description="Payout method: mobile_money, bank_transfer")
    payout_account: str = Field(..., description="Phone number or bank account")
    currency: str = Field(default="TZS", description="Currency code for payout")
    full_name: Optional[str] = None
    bank_name: Optional[str] = None  # For bank transfers
    account_name: Optional[str] = None  # For bank transfers


class FlutterwaveWebhookData(BaseModel):
    event: str
    data: dict

