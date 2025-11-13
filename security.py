"""
Security utilities and middleware for the Sokoni Africa API
"""
import time
import hashlib
import secrets
from typing import Optional, Dict, List
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import logging

logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
_rate_limit_storage: Dict[str, List[float]] = defaultdict(list)
_failed_login_attempts: Dict[str, Dict[str, any]] = defaultdict(dict)

# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "/api/auth/login": {"max_requests": 5, "window_seconds": 300},  # 5 attempts per 5 minutes
    "/api/auth/register": {"max_requests": 3, "window_seconds": 600},  # 3 attempts per 10 minutes
    "/api/auth/forgot-password": {"max_requests": 3, "window_seconds": 600},
    "/api/auth/reset-password": {"max_requests": 5, "window_seconds": 300},
    "/api/products": {"max_requests": 200, "window_seconds": 60},  # Higher limit for product listing
    "/api/uploads": {"max_requests": 500, "window_seconds": 60},  # High limit for image serving
    "/static": {"max_requests": 500, "window_seconds": 60},  # High limit for static files
    "default": {"max_requests": 200, "window_seconds": 60},  # Increased default to 200 requests per minute
}

# Account lockout configuration
ACCOUNT_LOCKOUT_CONFIG = {
    "max_attempts": 5,
    "lockout_duration_seconds": 900,  # 15 minutes
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Remove server header to hide server information (use del instead of pop)
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static files
        path = request.url.path
        if path in ["/api/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Skip rate limiting for image/static file requests (they're served directly)
        if path.startswith("/api/uploads/") or path.startswith("/static/"):
            return await call_next(request)
        
        # Get client identifier (IP address or user ID if authenticated)
        client_id = request.client.host if request.client else "unknown"
        
        # Check if user is authenticated and use user ID for rate limiting
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # Extract user ID from token (simplified - in production, decode properly)
                token = auth_header.split(" ")[1]
                # Use token hash as identifier for authenticated users
                client_id = f"user_{hashlib.sha256(token.encode()).hexdigest()[:16]}"
            except Exception:
                pass
        
        # Get rate limit config for this endpoint (check if path starts with any configured endpoint)
        endpoint = path
        config = RATE_LIMIT_CONFIG.get(endpoint, None)
        
        # If no exact match, check if path starts with any configured endpoint
        if config is None:
            for configured_endpoint, endpoint_config in RATE_LIMIT_CONFIG.items():
                if configured_endpoint != "default" and path.startswith(configured_endpoint):
                    config = endpoint_config
                    break
        
        # Use default if no match found
        if config is None:
            config = RATE_LIMIT_CONFIG["default"]
        
        # Clean old entries
        current_time = time.time()
        window_start = current_time - config["window_seconds"]
        _rate_limit_storage[client_id] = [
            timestamp for timestamp in _rate_limit_storage[client_id]
            if timestamp > window_start
        ]
        
        # Check rate limit
        if len(_rate_limit_storage[client_id]) >= config["max_requests"]:
            logger.warning(f"Rate limit exceeded for {client_id} on {endpoint}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Maximum {config['max_requests']} requests per {config['window_seconds']} seconds."
                },
                headers={"Retry-After": str(config["window_seconds"])}
            )
        
        # Record this request
        _rate_limit_storage[client_id].append(current_time)
        
        response = await call_next(request)
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks"""
    
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.MAX_REQUEST_SIZE:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": f"Request body too large. Maximum size is {self.MAX_REQUEST_SIZE / 1024 / 1024} MB"}
                    )
            except ValueError:
                pass
        
        response = await call_next(request)
        return response


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Log security-related events"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request (with error handling)
        try:
            client_ip = request.client.host if request.client else "unknown"
            logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
        except Exception:
            pass
        
        try:
            response = await call_next(request)
        except HTTPException as e:
            # Log security-related errors
            try:
                client_ip = request.client.host if request.client else "unknown"
                if e.status_code in [401, 403, 429]:
                    logger.warning(f"Security event: {e.status_code} - {e.detail} from {client_ip}")
            except Exception:
                pass
            raise
        except Exception as e:
            try:
                client_ip = request.client.host if request.client else "unknown"
                logger.error(f"Error processing request: {e} from {client_ip}")
            except Exception:
                pass
            raise
        
        # Log response time (with error handling)
        try:
            process_time = time.time() - start_time
            if hasattr(response, 'headers'):
                response.headers["X-Process-Time"] = str(process_time)
            
            # Log slow requests (potential DoS)
            if process_time > 5.0:
                logger.warning(f"Slow request: {request.url.path} took {process_time:.2f}s")
        except Exception:
            pass
        
        return response


def check_account_lockout(identifier: str):
    """
    Check if account is locked out due to failed login attempts.
    Returns (is_locked, lockout_message) as tuple
    """
    if identifier not in _failed_login_attempts:
        return False, None
    
    attempts_data = _failed_login_attempts[identifier]
    
    # Check if lockout period has expired
    if "locked_until" in attempts_data:
        locked_until = attempts_data["locked_until"]
        if datetime.utcnow() < locked_until:
            remaining = (locked_until - datetime.utcnow()).total_seconds()
            return True, f"Account temporarily locked. Try again in {int(remaining / 60)} minutes."
        else:
            # Lockout expired, reset
            del _failed_login_attempts[identifier]
            return False, None
    
    return False, None


def record_failed_login_attempt(identifier: str):
    """Record a failed login attempt"""
    if identifier not in _failed_login_attempts:
        _failed_login_attempts[identifier] = {
            "attempts": 0,
            "first_attempt": datetime.utcnow()
        }
    
    attempts_data = _failed_login_attempts[identifier]
    attempts_data["attempts"] += 1
    
    # Lock account if max attempts reached
    if attempts_data["attempts"] >= ACCOUNT_LOCKOUT_CONFIG["max_attempts"]:
        attempts_data["locked_until"] = datetime.utcnow() + timedelta(
            seconds=ACCOUNT_LOCKOUT_CONFIG["lockout_duration_seconds"]
        )
        logger.warning(f"Account locked: {identifier} after {attempts_data['attempts']} failed attempts")
        return True
    
    return False


def reset_failed_login_attempts(identifier: str):
    """Reset failed login attempts after successful login"""
    if identifier in _failed_login_attempts:
        del _failed_login_attempts[identifier]


def validate_password_strength(password: str):
    """
    Validate password strength.
    Returns (is_valid, error_message) as tuple
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not (has_upper and has_lower and has_digit):
        return False, "Password must contain at least one uppercase letter, one lowercase letter, and one digit"
    
    # Check for common weak passwords
    common_passwords = ["password", "12345678", "qwerty", "abc123", "password123"]
    if password.lower() in common_passwords:
        return False, "Password is too common. Please choose a stronger password"
    
    return True, None


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if text is None:
        return ""
    
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return ""
    
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove potentially dangerous characters (but allow normal text)
    # In production, use a proper HTML sanitizer like bleach
    dangerous_chars = ["<script", "javascript:", "onerror=", "onload="]
    text_lower = text.lower()
    for char in dangerous_chars:
        if char in text_lower:
            text = text.replace(char, "")
    
    return text.strip()


def generate_csrf_token() -> str:
    """Generate a CSRF token"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """Verify CSRF token using constant-time comparison"""
    return secrets.compare_digest(token, stored_token)


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging/storage"""
    return hashlib.sha256(data.encode()).hexdigest()


def is_safe_origin(origin: str, allowed_origins: List[str]) -> bool:
    """Check if origin is safe"""
    if "*" in allowed_origins:
        return True
    
    return origin in allowed_origins

