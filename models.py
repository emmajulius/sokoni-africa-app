from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
from datetime import datetime, timezone


class UserType(str, enum.Enum):
    CLIENT = "client"
    SUPPLIER = "supplier"
    RETAILER = "retailer"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String, nullable=True)  # Null for Google sign-in
    user_type = Column(SQLEnum(UserType), default=UserType.CLIENT)
    gender = Column(SQLEnum(Gender), nullable=True)
    profile_image = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_guest = Column(Boolean, default=False)
    google_id = Column(String, unique=True, nullable=True, index=True)
    # Location fields
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_address = Column(String, nullable=True)  # Human-readable address
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    products = relationship("Product", back_populates="seller", foreign_keys="Product.seller_id")
    orders = relationship("Order", back_populates="customer", foreign_keys="Order.customer_id")
    sold_orders = relationship("Order", back_populates="seller", foreign_keys="Order.seller_id")
    stories = relationship("Story", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    # Auction relationships
    bids = relationship("Bid", back_populates="bidder", foreign_keys="Bid.bidder_id")
    auction_products_as_bidder = relationship("Product", foreign_keys="Product.current_bidder_id", viewonly=True)
    auction_products_as_winner = relationship("Product", foreign_keys="Product.winner_id", viewonly=True)


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    products = relationship("Product", back_populates="category_obj")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)  # Stored in Sokocoin
    local_price = Column(Float, nullable=True)  # Original price in seller's local currency
    local_currency = Column(String, nullable=True)  # Seller's local currency code (TZS, KES, NGN, etc.)
    category = Column(String, index=True)  # Category slug for filtering
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id"))
    
    # Images
    image_url = Column(String, nullable=True)
    images = Column(JSON, default=list)  # Array of image URLs
    
    # Product details
    unit_type = Column(String, nullable=True)  # piece, kg, liter, etc.
    stock_quantity = Column(Integer, nullable=True)
    
    # Features
    is_winga_enabled = Column(Boolean, default=False)
    has_warranty = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)
    is_adult_content = Column(Boolean, default=False)
    is_sponsored = Column(Boolean, default=False)
    
    # Auction fields
    is_auction = Column(Boolean, default=False)
    starting_price = Column(Float, nullable=True)  # Starting bid price in Sokocoin
    bid_increment = Column(Float, nullable=True)  # Minimum bid increment in Sokocoin
    auction_duration_hours = Column(Float, nullable=True)  # Auction duration in hours (supports decimal for minutes)
    auction_start_time = Column(DateTime(timezone=True), nullable=True)  # When auction starts
    auction_end_time = Column(DateTime(timezone=True), nullable=True)  # When auction ends
    current_bid = Column(Float, nullable=True)  # Current highest bid in Sokocoin
    current_bidder_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Current highest bidder
    auction_status = Column(String, default="pending")  # pending, active, ended, cancelled
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Winner user ID after auction ends
    winner_paid = Column(Boolean, default=False)  # Whether winner has completed payment
    
    # Engagement
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    tags = Column(JSON, default=list)  # Array of tags
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    seller = relationship("User", back_populates="products", foreign_keys=[seller_id])
    category_obj = relationship("Category", back_populates="products")
    cart_items = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    current_bidder = relationship("User", foreign_keys=[current_bidder_id])
    winner = relationship("User", foreign_keys=[winner_id])
    bids = relationship("Bid", back_populates="product", cascade="all, delete-orphan")


class Bid(Base):
    __tablename__ = "bids"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    bidder_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bid_amount = Column(Float, nullable=False)  # Bid amount in Sokocoin
    bid_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_winning_bid = Column(Boolean, default=False)  # True if this is the current winning bid
    is_outbid = Column(Boolean, default=False)  # True if this bid was outbid by a higher bid
    
    # Relationships
    product = relationship("Product", back_populates="bids")
    bidder = relationship("User", foreign_keys=[bidder_id])


class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    media_url = Column(String)
    media_type = Column(String)  # image, video
    caption = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True))
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="stories")


class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"))
    seller_id = Column(Integer, ForeignKey("users.id"))
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Float)
    processing_fee = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=0.0)
    shipping_distance_km = Column(Float, nullable=True)
    includes_shipping = Column(Boolean, default=False)
    shipping_address = Column(Text)
    payment_method = Column(String, nullable=True)
    payment_status = Column(String, default="pending")  # pending, paid, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="orders")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="sold_orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price = Column(Float)  # Price at time of order
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class OTP(Base):
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def is_expired(self):
        """Check if OTP has expired"""
        # Use UTC-aware datetime for comparison
        now = datetime.now(timezone.utc)
        # Ensure expires_at is timezone-aware
        if self.expires_at.tzinfo is None:
            # If expires_at is naive, assume it's UTC
            expires_at_aware = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at_aware = self.expires_at
        return now > expires_at_aware


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])


class ProductReport(Base):
    __tablename__ = "product_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=False)  # spam, inappropriate, fake, other
    description = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, reviewed, resolved, dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product")
    reporter = relationship("User", foreign_keys=[reporter_id])


class SavedProduct(Base):
    __tablename__ = "saved_products"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    product = relationship("Product")


class KYCDocument(Base):
    __tablename__ = "kyc_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_type = Column(String, nullable=False)  # id_card, passport, driver_license, etc.
    document_url = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who reviewed
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(String, nullable=False)  # like, comment, order, message, follow, etc.
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    
    # Related entity IDs (optional, for navigation)
    related_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    related_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    related_order_id = Column(Integer, nullable=True)
    related_conversation_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    related_user = relationship("User", foreign_keys=[related_user_id])
    related_product = relationship("Product", foreign_keys=[related_product_id])


class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who follows
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User being followed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    follower = relationship("User", foreign_keys=[follower_id])
    following = relationship("User", foreign_keys=[following_id])
    
    # Unique constraint: a user can only follow another user once
    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='unique_follow'),
    )


class ProductLike(Base):
    __tablename__ = "product_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product")
    user = relationship("User", foreign_keys=[user_id])
    
    # Unique constraint: a user can only like a product once
    __table_args__ = (
        UniqueConstraint('product_id', 'user_id', name='unique_product_like'),
    )


class ProductComment(Base):
    __tablename__ = "product_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product = relationship("Product")
    user = relationship("User", foreign_keys=[user_id])


class ProductRating(Base):
    __tablename__ = "product_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Float, nullable=False)  # Rating from 1.0 to 5.0
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product = relationship("Product")
    user = relationship("User", foreign_keys=[user_id])
    
    # Unique constraint: a user can only rate a product once (but can update)
    __table_args__ = (
        UniqueConstraint('product_id', 'user_id', name='unique_product_rating'),
    )


class WalletTransactionType(str, enum.Enum):
    TOPUP = "topup"
    CASHOUT = "cashout"
    PURCHASE = "purchase"
    EARN = "earn"
    REFUND = "refund"
    FEE = "fee"


class WalletTransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    sokocoin_balance = Column(Float, default=0.0, nullable=False)  # In-app currency balance
    total_earned = Column(Float, default=0.0, nullable=False)  # Total Sokocoin earned
    total_spent = Column(Float, default=0.0, nullable=False)  # Total Sokocoin spent
    total_topup = Column(Float, default=0.0, nullable=False)  # Total top-up amount
    total_cashout = Column(Float, default=0.0, nullable=False)  # Total cashout amount
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    transactions = relationship("WalletTransaction", back_populates="wallet")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    transaction_type = Column(SQLEnum(WalletTransactionType), nullable=False, index=True)
    status = Column(SQLEnum(WalletTransactionStatus), default=WalletTransactionStatus.PENDING, index=True)
    
    # Amounts
    sokocoin_amount = Column(Float, nullable=False)  # Amount in Sokocoin
    local_currency_amount = Column(Float, nullable=True)  # Equivalent in local currency
    local_currency_code = Column(String, nullable=True)  # e.g., "TZS", "KES", "NGN"
    exchange_rate = Column(Float, nullable=True)  # Rate used for conversion
    
    # Payment gateway details
    payment_gateway = Column(String, nullable=True)  # "flutterwave", etc.
    payment_reference = Column(String, nullable=True, index=True)  # Gateway transaction reference
    gateway_transaction_id = Column(String, nullable=True, index=True)
    
    # Payout details (for cashout)
    payout_method = Column(String, nullable=True)  # "mobile_money", "bank_transfer"
    payout_account = Column(String, nullable=True)  # Phone number or bank account
    payout_reference = Column(String, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)  # Additional data (renamed from metadata to avoid SQLAlchemy conflict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
    user = relationship("User", foreign_keys=[user_id])


class AdminCashoutStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AdminFeeCollection(Base):
    """Track fees collected from orders"""
    __tablename__ = "admin_fee_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    processing_fee = Column(Float, default=0.0, nullable=False)
    shipping_fee = Column(Float, default=0.0, nullable=False)
    total_fee = Column(Float, nullable=False)  # processing_fee + shipping_fee
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    order = relationship("Order", foreign_keys=[order_id])


class AdminCashout(Base):
    """Track admin cashout requests"""
    __tablename__ = "admin_cashouts"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)  # Amount in SOK
    currency = Column(String, nullable=True)  # Local currency code (TZS, KES, NGN, etc.)
    local_currency_amount = Column(Float, nullable=True)  # Amount in local currency
    exchange_rate = Column(Float, nullable=True)  # Exchange rate used for conversion
    payout_method = Column(String, nullable=False)  # "mobile_money", "bank_transfer"
    payout_account = Column(String, nullable=False)  # Phone number for mobile_money, account number for bank_transfer
    payout_account_name = Column(String, nullable=True)  # Account holder name
    # Bank transfer specific fields
    bank_name = Column(String, nullable=True)  # Bank name
    bank_account_number = Column(String, nullable=True)  # Bank account number
    bank_account_holder = Column(String, nullable=True)  # Bank account holder name
    bank_branch = Column(String, nullable=True)  # Bank branch name/location
    bank_swift_code = Column(String, nullable=True)  # SWIFT/BIC code (for international transfers)
    status = Column(SQLEnum(AdminCashoutStatus), default=AdminCashoutStatus.PENDING, index=True)
    notes = Column(Text, nullable=True)  # Admin notes
    rejection_reason = Column(Text, nullable=True)  # If rejected
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who processed
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    processor = relationship("User", foreign_keys=[processed_by])

