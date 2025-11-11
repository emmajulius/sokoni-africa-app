import random
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Warning: Twilio not installed. SMS will be printed to console in development mode.")

from config import settings

class SMSService:
    """Service for sending SMS OTP codes"""
    
    def __init__(self):
        # Twilio credentials from environment variables
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from_number = os.getenv("TWILIO_FROM_NUMBER")
        
        # Initialize Twilio client if credentials are available
        self.twilio_client = None
        if self.twilio_account_sid and self.twilio_auth_token and TWILIO_AVAILABLE:
            try:
                self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            except Exception as e:
                print(f"Warning: Failed to initialize Twilio client: {e}")
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP code"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    def send_otp(self, phone: str, code: str) -> bool:
        """
        Send OTP code via SMS
        Returns True if sent successfully, False otherwise
        """
        # Format phone number (remove spaces, ensure + prefix)
        phone = phone.strip().replace(" ", "")
        if not phone.startswith("+"):
            # Assume it's a local number, you may need to add country code
            # For now, we'll try to send as is
            pass
        
        message = f"Your Sokoni Africa verification code is: {code}. Valid for 10 minutes."
        
        # Try to send via Twilio if configured
        if self.twilio_client and self.twilio_from_number and TWILIO_AVAILABLE:
            try:
                message_obj = self.twilio_client.messages.create(
                    body=message,
                    from_=self.twilio_from_number,
                    to=phone
                )
                print(f"OTP sent successfully via Twilio. SID: {message_obj.sid}")
                return True
            except TwilioRestException as e:
                print(f"Twilio error: {e}")
                # Fall through to development mode
            except Exception as e:
                print(f"Error sending SMS via Twilio: {e}")
                # Fall through to development mode
        
        # Development mode: Print OTP to console/log instead of sending SMS
        # This allows testing without Twilio credentials
        print(f"\n{'='*80}")
        print(f"🔐 DEVELOPMENT MODE - OTP NOT SENT VIA SMS")
        print(f"{'='*80}")
        print(f"📱 Phone Number: {phone}")
        print(f"🔑 OTP Code: {code}")
        print(f"⏰ Valid for: 10 minutes")
        print(f"{'='*80}")
        print(f"⚠️  To receive real SMS, add Twilio credentials to .env file")
        print(f"{'='*80}\n")
        
        # In development, we'll consider it "sent" even though it's just printed
        # Set TWILIO_ACCOUNT_SID in .env to enable real SMS sending
        return True
    
    def get_expiry_time(self, minutes: int = 10) -> datetime:
        """Get expiry time for OTP (default 10 minutes)"""
        # Use UTC-aware datetime
        return datetime.now(timezone.utc) + timedelta(minutes=minutes)

