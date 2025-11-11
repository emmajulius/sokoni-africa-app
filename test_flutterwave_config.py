"""
Test script to verify Flutterwave configuration
Run this to check if Flutterwave API keys are properly configured
"""
from config import settings
from flutterwave_service import FlutterwaveService

def test_flutterwave_config():
    print("=" * 60)
    print("Flutterwave Configuration Test")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("1. Environment Variables:")
    print(f"   FLW_SECRET_KEY: {'✓ SET' if settings.FLW_SECRET_KEY else '✗ NOT SET'}")
    if settings.FLW_SECRET_KEY:
        print(f"      Value: {settings.FLW_SECRET_KEY[:20]}... (length: {len(settings.FLW_SECRET_KEY)})")
    
    print(f"   FLW_PUBLIC_KEY: {'✓ SET' if settings.FLW_PUBLIC_KEY else '✗ NOT SET'}")
    if settings.FLW_PUBLIC_KEY:
        print(f"      Value: {settings.FLW_PUBLIC_KEY[:20]}... (length: {len(settings.FLW_PUBLIC_KEY)})")
    
    print(f"   FLW_ENCRYPTION_KEY: {'✓ SET' if settings.FLW_ENCRYPTION_KEY else '✗ NOT SET'}")
    if settings.FLW_ENCRYPTION_KEY:
        print(f"      Value: {settings.FLW_ENCRYPTION_KEY[:20]}... (length: {len(settings.FLW_ENCRYPTION_KEY)})")
    
    print()
    
    # Check FlutterwaveService
    print("2. FlutterwaveService Initialization:")
    try:
        fw_service = FlutterwaveService()
        print(f"   Secret Key: {'✓ SET' if fw_service.secret_key else '✗ NOT SET'}")
        print(f"   Public Key: {'✓ SET' if fw_service.public_key else '✗ NOT SET'}")
        print(f"   Base URL: {fw_service.base_url}")
        print(f"   Authorization Header: Bearer {fw_service.secret_key[:20]}...")
        print("   ✓ FlutterwaveService initialized successfully")
    except Exception as e:
        print(f"   ✗ Error initializing FlutterwaveService: {e}")
    
    print()
    
    # Configuration check
    print("3. Configuration Check:")
    if settings.FLW_SECRET_KEY and settings.FLW_PUBLIC_KEY:
        print("   ✓ Both keys are configured")
        print("   ✓ Configuration check will PASS")
    else:
        print("   ✗ Missing required keys")
        print("   ✗ Configuration check will FAIL")
        if not settings.FLW_SECRET_KEY:
            print("      - FLW_SECRET_KEY is missing")
        if not settings.FLW_PUBLIC_KEY:
            print("      - FLW_PUBLIC_KEY is missing")
    
    print()
    print("=" * 60)
    print("Note: If keys are set but server still shows error,")
    print("      RESTART the backend server to load new .env values")
    print("=" * 60)

if __name__ == "__main__":
    test_flutterwave_config()

