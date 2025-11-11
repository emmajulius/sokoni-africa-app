from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta, timezone
from database import get_db
from models import User, OTP
from schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    OTPSendRequest, OTPVerifyRequest, OTPSendResponse, OTPVerifyResponse
)
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from models import UserType
from sms_service import SMSService
from email_service import EmailService
from pydantic import BaseModel, EmailStr
import requests
import json
from typing import Optional, Dict, Any

router = APIRouter()
sms_service = SMSService()
email_service = EmailService()


def verify_google_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Google ID token and extract user information.
    Returns user info dict with 'sub' (Google ID), 'email', 'name', etc. if valid, None otherwise.
    """
    try:
        if not id_token or not id_token.strip():
            print(f"[Google Auth] ERROR: Empty or invalid token provided")
            return None
            
        print(f"[Google Auth] Verifying token (length: {len(id_token)})")
        print(f"[Google Auth] Token preview: {id_token[:50]}...")
        
        # Verify the token with Google's API
        # For production, you should verify the token signature using google-auth library
        # For now, we'll use a simpler approach: verify with Google's tokeninfo endpoint
        try:
            response = requests.get(
                f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}',
                timeout=10
            )
        except requests.exceptions.Timeout:
            print(f"[Google Auth] ERROR: Request timeout while verifying token")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[Google Auth] ERROR: Request exception: {type(e).__name__}: {e}")
            return None
        
        print(f"[Google Auth] Tokeninfo response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[Google Auth] Token verification failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"[Google Auth] Error response: {error_data}")
            except:
                print(f"[Google Auth] Error response text: {response.text[:500]}")
            return None
        
        try:
            token_info = response.json()
        except json.JSONDecodeError as e:
            print(f"[Google Auth] ERROR: Failed to parse JSON response: {e}")
            print(f"[Google Auth] Response text: {response.text[:500]}")
            return None
            
        print(f"[Google Auth] Token info received: {list(token_info.keys())}")
        
        # Verify the token is for our app (check audience if needed)
        # For now, we'll just verify it's a valid Google token
        if 'error' in token_info:
            error_msg = token_info.get('error', 'Unknown error')
            error_description = token_info.get('error_description', '')
            print(f"[Google Auth] Token verification error: {error_msg} - {error_description}")
            return None
        
        # Extract user information
        user_info = {
            'sub': token_info.get('sub'),  # Google user ID
            'email': token_info.get('email'),
            'email_verified': token_info.get('email_verified', 'false') == 'true',
            'name': token_info.get('name'),
            'picture': token_info.get('picture'),
            'given_name': token_info.get('given_name'),
            'family_name': token_info.get('family_name'),
        }
        
        # Validate required fields
        if not user_info.get('sub') or not user_info.get('email'):
            print(f"[Google Auth] ERROR: Missing required fields in token info. sub={user_info.get('sub')}, email={user_info.get('email')}")
            return None
        
        print(f"[Google Auth] Successfully extracted user info: email={user_info.get('email')}, sub={user_info.get('sub')}")
        return user_info
    except Exception as e:
        print(f"[Google Auth] ERROR: Unexpected error verifying Google token: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


class ResetPasswordRequest(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    code: str
    new_password: str

    def clean_contact(self):
        if self.phone:
            return "phone", self.phone.strip()
        if self.email:
            return "email", self.email.strip()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either phone or email must be provided"
        )


class ForgotPasswordEmailRequest(BaseModel):
    email: EmailStr


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists (if provided)
    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if phone already exists (if provided)
    if user_data.phone and db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Validate password length (bcrypt has 72-byte limit)
    if user_data.password:
        password_bytes = user_data.password.encode('utf-8')
        if len(password_bytes) > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too long. Maximum length is 72 characters."
            )
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
    
    # Create new user
    hashed_password = None
    if user_data.password:
        hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        hashed_password=hashed_password,
        user_type=user_data.user_type,
        gender=user_data.gender,
        google_id=user_data.google_id,
        is_guest=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token (sub must be a string for JWT)
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    # Create UserResponse with default stats for new user
    user_response = UserResponse(
        id=db_user.id,
        username=db_user.username,
        full_name=db_user.full_name,
        email=db_user.email,
        phone=db_user.phone,
        user_type=db_user.user_type,
        gender=db_user.gender,
        profile_image=db_user.profile_image,
        is_active=db_user.is_active,
        is_verified=db_user.is_verified,
        followers_count=0,
        following_count=0,
        sold_products_count=0,
        rating=0.0,
        created_at=db_user.created_at,
    )
    
    return Token(access_token=access_token, user=user_response)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user with username/phone/email and password or Google token"""
    user = None
    
    if credentials.google_token:
        # Google Sign-In - verify token and extract user info
        print(f"[Google Auth] Login attempt with Google token")
        google_user_info = verify_google_token(credentials.google_token)
        
        if not google_user_info:
            print(f"[Google Auth] Token verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token. Please try signing in again."
            )
        
        google_id = google_user_info.get('sub')
        google_email = google_user_info.get('email')
        
        print(f"[Google Auth] Looking for user with google_id={google_id}, email={google_email}")
        
        if not google_id or not google_email:
            print(f"[Google Auth] Missing user info: google_id={google_id}, email={google_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token: missing user information"
            )
        
        # Try to find user by google_id first (most reliable)
        user = db.query(User).filter(User.google_id == google_id).first()
        print(f"[Google Auth] User found by google_id: {user is not None}")
        
        # If not found by google_id, try by email (for users registered before google_id was added)
        if not user and google_email:
            user = db.query(User).filter(User.email == google_email).first()
            print(f"[Google Auth] User found by email: {user is not None}")
            # If user exists but doesn't have google_id, update it
            if user and not user.google_id:
                print(f"[Google Auth] Updating user with google_id")
                user.google_id = google_id
                db.commit()
                db.refresh(user)
        
        # If still no user found, return error so frontend can register
        if not user:
            print(f"[Google Auth] User not found - returning 404 for registration")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please register first."
            )
        
        print(f"[Google Auth] User found: {user.username} (ID: {user.id})")
    else:
        # Regular login - support username, phone, or email
        if not credentials.password:
            print(f"[Login] Password is required")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required"
            )
        
        # Try username first, then phone, then email
        user = None
        identifier_used = None
        
        if credentials.username:
            print(f"[Login] Attempting login with username: {credentials.username}")
            user = db.query(User).filter(User.username == credentials.username).first()
            identifier_used = "username"
        elif credentials.phone:
            print(f"[Login] Attempting login with phone: {credentials.phone}")
            user = db.query(User).filter(User.phone == credentials.phone).first()
            identifier_used = "phone"
        elif credentials.email:
            print(f"[Login] Attempting login with email: {credentials.email}")
            user = db.query(User).filter(User.email == credentials.email).first()
            identifier_used = "email"
        else:
            print(f"[Login] No identifier provided (username, phone, or email)")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username, email, or phone number is required"
            )
        
        if not user:
            print(f"[Login] User not found with {identifier_used}: {credentials.username or credentials.phone or credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email/phone or password"
            )
        
        if not user.hashed_password:
            print(f"[Login] User {user.username} (ID: {user.id}) has no password hash (may be Google-only account)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This account doesn't have a password. Please use Google Sign-In or reset your password."
            )
        
        print(f"[Login] User found: {user.username} (ID: {user.id}), verifying password...")
        if not verify_password(credentials.password, user.hashed_password):
            print(f"[Login] Password verification failed for user: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email/phone or password"
            )
        
        print(f"[Login] Password verified successfully for user: {user.username}")
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token (sub must be a string for JWT)
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # Create UserResponse with computed stats (use defaults for login to avoid heavy queries)
    # For login, we use default values for stats to keep response fast
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        user_type=user.user_type,
        gender=user.gender,
        profile_image=user.profile_image,
        is_active=user.is_active,
        is_verified=user.is_verified,
        followers_count=0,  # Use defaults for login (can be fetched later if needed)
        following_count=0,
        sold_products_count=0,
        rating=0.0,
        created_at=user.created_at,
    )
    
    return Token(access_token=access_token, user=user_response)


@router.post("/guest", response_model=Token)
async def login_as_guest(user_type: UserType = UserType.CLIENT, db: Session = Depends(get_db)):
    """Login as guest user"""
    # Create or get guest user
    guest_username = f"guest_{datetime.now().timestamp()}"
    db_user = User(
        username=guest_username,
        full_name="Guest User",
        user_type=user_type,
        is_guest=True,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token (sub must be a string for JWT)
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    # Create UserResponse with default stats for guest user
    user_response = UserResponse(
        id=db_user.id,
        username=db_user.username,
        full_name=db_user.full_name,
        email=db_user.email,
        phone=db_user.phone,
        user_type=db_user.user_type,
        gender=db_user.gender,
        profile_image=db_user.profile_image,
        is_active=db_user.is_active,
        is_verified=db_user.is_verified,
        followers_count=0,
        following_count=0,
        sold_products_count=0,
        rating=0.0,
        created_at=db_user.created_at,
    )
    
    return Token(access_token=access_token, user=user_response)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information"""
    # Import the stats calculation function from users router
    from app.routers.users import _calculate_user_stats
    stats = _calculate_user_stats(current_user, db)
    
    user_response = UserResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        user_type=current_user.user_type,
        gender=current_user.gender,
        profile_image=current_user.profile_image,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        followers_count=stats['followers_count'],
        following_count=stats['following_count'],
        sold_products_count=stats['sold_products_count'],
        rating=stats['rating'],
        created_at=current_user.created_at,
    )
    
    return user_response


@router.post("/send-otp", response_model=OTPSendResponse)
async def send_otp(request: OTPSendRequest, db: Session = Depends(get_db)):
    """Send OTP code to phone number for verification"""
    phone = request.phone.strip()
    
    # Validate phone number format (basic validation)
    if not phone or len(phone) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )
    
    # Generate OTP code
    otp_code = sms_service.generate_otp(length=6)
    expires_at = sms_service.get_expiry_time(minutes=10)
    
    # Invalidate any existing unused OTPs for this phone
    db.query(OTP).filter(
        OTP.phone == phone,
        OTP.is_used == False
    ).update({"is_used": True})
    
    # Create new OTP record
    db_otp = OTP(
        phone=phone,
        code=otp_code,
        expires_at=expires_at,
        is_used=False
    )
    db.add(db_otp)
    db.commit()
    
    # Send OTP via SMS
    sms_sent = sms_service.send_otp(phone, otp_code)
    
    if sms_sent:
        return OTPSendResponse(
            success=True,
            message=f"OTP sent successfully to {phone}",
            expires_in_minutes=10
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )


@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(request: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Verify OTP code for phone number"""
    phone = request.phone.strip()
    code = request.code.strip()
    
    print(f"\n{'='*60}")
    print(f"🔍 VERIFYING OTP")
    print(f"{'='*60}")
    print(f"📱 Phone: {phone}")
    print(f"🔑 Code: {code}")
    print(f"{'='*60}\n")
    
    # Find the most recent unused OTP for this phone
    db_otp = db.query(OTP).filter(
        OTP.phone == phone,
        OTP.code == code,
        OTP.is_used == False
    ).order_by(OTP.created_at.desc()).first()
    
    if not db_otp:
        # Let's check what OTPs exist for this phone
        all_otps = db.query(OTP).filter(OTP.phone == phone).order_by(OTP.created_at.desc()).limit(5).all()
        print(f"❌ No matching OTP found for phone: {phone}")
        print(f"📋 Recent OTPs for this phone:")
        for otp in all_otps:
            print(f"   - Code: {otp.code}, Used: {otp.is_used}, Expired: {otp.is_expired()}, Created: {otp.created_at}")
        print(f"{'='*60}\n")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP code. Please check the code and try again."
        )
    
    # Check if OTP is expired
    if db_otp.is_expired():
        db_otp.is_used = True
        db.commit()
        print(f"❌ OTP expired for phone: {phone}")
        print(f"{'='*60}\n")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired. Please request a new one."
        )
    
    print(f"✅ OTP verified successfully!")
    print(f"{'='*60}\n")
    
    # Mark OTP as used
    db_otp.is_used = True
    db.commit()
    
    # Check if user exists with this phone number
    user = db.query(User).filter(User.phone == phone).first()
    
    if user:
        # User exists - login flow
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create access token (sub must be a string for JWT)
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # Create UserResponse with default stats for OTP login
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            user_type=user.user_type,
            gender=user.gender,
            profile_image=user.profile_image,
            is_active=user.is_active,
            is_verified=user.is_verified,
            followers_count=0,
            following_count=0,
            sold_products_count=0,
            rating=0.0,
            created_at=user.created_at,
        )
        
        return OTPVerifyResponse(
            success=True,
            message="Phone verified successfully. Login successful.",
            token=access_token,
            user=user_response
        )
    else:
        # User doesn't exist - registration flow
        # Return success with token for registration completion
        # The frontend should then call the register endpoint
        return OTPVerifyResponse(
            success=True,
            message="Phone verified successfully. You can now complete registration.",
            token=None,
            user=None
        )


@router.post("/register-with-phone", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_with_phone(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user after phone verification"""
    if not user_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required"
        )
    
    # Check if phone already registered
    if db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Verify OTP was used for this phone (within last 30 minutes)
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    db_otp = db.query(OTP).filter(
        OTP.phone == user_data.phone,
        OTP.is_used == True,
        OTP.created_at >= recent_time
    ).order_by(OTP.created_at.desc()).first()
    
    if not db_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please verify your phone number first by completing OTP verification"
        )
    
    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists (if provided)
    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password length (bcrypt has 72-byte limit)
    if user_data.password:
        password_bytes = user_data.password.encode('utf-8')
        if len(password_bytes) > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too long. Maximum length is 72 characters."
            )
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
    
    # Create new user
    hashed_password = None
    if user_data.password:
        hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        hashed_password=hashed_password,
        user_type=user_data.user_type,
        gender=user_data.gender,
        google_id=user_data.google_id,
        is_guest=False,
        is_verified=True  # Phone is verified
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token (sub must be a string for JWT)
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    # Create UserResponse with default stats for new user
    user_response = UserResponse(
        id=db_user.id,
        username=db_user.username,
        full_name=db_user.full_name,
        email=db_user.email,
        phone=db_user.phone,
        user_type=db_user.user_type,
        gender=db_user.gender,
        profile_image=db_user.profile_image,
        is_active=db_user.is_active,
        is_verified=db_user.is_verified,
        followers_count=0,
        following_count=0,
        sold_products_count=0,
        rating=0.0,
        created_at=db_user.created_at,
    )
    
    return Token(access_token=access_token, user=user_response)


@router.post("/forgot-password", response_model=OTPSendResponse)
async def forgot_password(request: OTPSendRequest, db: Session = Depends(get_db)):
    """Send OTP to phone number for password recovery"""
    phone = request.phone.strip()
    
    # Validate phone number format
    if not phone or len(phone) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number format"
        )
    
    # Check if user exists with this phone
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this phone number"
        )
    
    # Generate OTP code
    otp_code = sms_service.generate_otp(length=6)
    expires_at = sms_service.get_expiry_time(minutes=10)
    
    # Invalidate any existing unused OTPs for this phone
    db.query(OTP).filter(
        OTP.phone == phone,
        OTP.is_used == False
    ).update({"is_used": True})
    
    # Create new OTP record
    db_otp = OTP(
        phone=phone,
        email=None,
        code=otp_code,
        expires_at=expires_at,
        is_used=False
    )
    db.add(db_otp)
    db.commit()
    
    # Send OTP via SMS
    sms_sent = sms_service.send_otp(phone, otp_code)
    
    if sms_sent:
        return OTPSendResponse(
            success=True,
            message=f"OTP sent successfully to {phone} for password recovery",
            expires_in_minutes=10
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )


@router.post("/forgot-password-email", response_model=OTPSendResponse)
async def forgot_password_email(
    request: ForgotPasswordEmailRequest,
    db: Session = Depends(get_db)
):
    """Send OTP to email for password recovery"""
    email = request.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address"
        )

    otp_code = sms_service.generate_otp(length=6)
    expires_at = sms_service.get_expiry_time(minutes=10)

    db.query(OTP).filter(
        OTP.email == email,
        OTP.is_used == False
    ).update({"is_used": True})

    db_otp = OTP(
        phone=None,
        email=email,
        code=otp_code,
        expires_at=expires_at,
        is_used=False
    )
    db.add(db_otp)
    db.commit()

    email_sent = email_service.send_password_reset_code(email, otp_code)

    if email_sent:
        return OTPSendResponse(
            success=True,
            message=f"Password reset instructions sent to {email}",
            expires_in_minutes=10
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset email. Please try again."
        )


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password after OTP verification"""
    contact_type, contact_value = request.clean_contact()
    code = request.code.strip()
    new_password = request.new_password
    
    # Verify OTP
    db_otp = (
        db.query(OTP)
        .filter(
            OTP.code == code,
            OTP.is_used == False,
            OTP.phone == contact_value if contact_type == "phone" else OTP.email == contact_value,
        )
        .order_by(OTP.created_at.desc())
        .first()
    )
    
    if not db_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code"
        )
    
    if db_otp.is_expired():
        db_otp.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired. Please request a new one."
        )
    
    # Find user
    if contact_type == "phone":
        user = db.query(User).filter(User.phone == contact_value).first()
    else:
        user = db.query(User).filter(User.email == contact_value).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate new password
    if not new_password or len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )
    
    # Validate password length (bcrypt has 72-byte limit)
    password_bytes = new_password.encode('utf-8')
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long. Maximum length is 72 characters."
        )
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    
    # Mark OTP as used
    db_otp.is_used = True
    
    db.commit()
    
    return {
        "success": True,
        "message": "Password reset successfully"
    }


