"""
Test Flutterwave API v3 with OAuth-style credentials
Flutterwave v4 credentials might need token exchange first
"""
import requests
import json
from config import settings
import base64

def test_flutterwave_oauth():
    print("=" * 60)
    print("Testing Flutterwave OAuth Token Exchange")
    print("=" * 60)
    print()
    
    client_id = settings.FLW_PUBLIC_KEY
    client_secret = settings.FLW_SECRET_KEY
    
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:20]}...")
    print()
    
    # Try to get OAuth token first (if v4 uses OAuth)
    token_url = "https://api.flutterwave.com/v3/oauth/token"
    
    # Method 1: Client credentials grant
    print("=" * 60)
    print("Method 1: OAuth Token Exchange (Client Credentials)")
    print("=" * 60)
    
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    try:
        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "client_credentials"
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"\n✅ Got access token: {access_token[:30]}...")
            
            # Now try to use this token for payments
            print("\n" + "=" * 60)
            print("Testing payment with OAuth token")
            print("=" * 60)
            
            payload = {
                "tx_ref": f"TEST_{1234567890}",
                "amount": 100,
                "currency": "TZS",
                "payment_options": "card",
                "redirect_url": "https://sokoni.africa/payment/callback",
                "customer": {
                    "email": "test@sokoni.app",
                    "name": "Test User",
                    "phone_number": "+255123456789"
                }
            }
            
            payment_response = requests.post(
                "https://api.flutterwave.com/v3/payments",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )
            
            print(f"Payment Status: {payment_response.status_code}")
            print(f"Payment Response: {payment_response.text[:500]}")
            
            if payment_response.status_code in [200, 201]:
                print("\n✅ SUCCESS: OAuth flow works!")
                return {
                    "method": "oauth",
                    "token_url": token_url,
                    "auth_header": f"Basic {auth_header}"
                }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Method 2: Direct Client Secret as Bearer (v3 style)
    print("\n" + "=" * 60)
    print("Method 2: Direct Client Secret as Bearer (v3)")
    print("=" * 60)
    
    payload = {
        "tx_ref": f"TEST_{1234567890}",
        "amount": 100,
        "currency": "TZS",
        "payment_options": "card",
        "redirect_url": "https://sokoni.africa/payment/callback",
        "customer": {
            "email": "test@sokoni.app",
            "name": "Test User",
            "phone_number": "+255123456789"
        }
    }
    
    try:
        response = requests.post(
            "https://api.flutterwave.com/v3/payments",
            headers={
                "Authorization": f"Bearer {client_secret}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code in [200, 201]:
            print("\n✅ SUCCESS: Direct Client Secret works!")
            return {
                "method": "direct",
                "headers": {
                    "Authorization": f"Bearer {client_secret}",
                    "Content-Type": "application/json"
                }
            }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Please check Flutterwave documentation for v4 API format")
    print("=" * 60)
    return None

if __name__ == "__main__":
    test_flutterwave_oauth()

