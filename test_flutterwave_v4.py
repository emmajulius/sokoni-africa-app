"""
Test Flutterwave API v4 call
"""
import requests
import json
from config import settings

def test_flutterwave_v4():
    print("=" * 60)
    print("Testing Flutterwave API v4")
    print("=" * 60)
    print()
    
    client_id = settings.FLW_PUBLIC_KEY
    client_secret = settings.FLW_SECRET_KEY
    base_url = "https://api.flutterwave.com/v4"
    
    print(f"Client ID: {client_id[:20]}...")
    print(f"Client Secret: {client_secret[:20]}...")
    print(f"Base URL: {base_url}")
    print()
    
    # Try different authentication methods for v4
    auth_methods = [
        {
            "name": "Bearer with Client Secret",
            "headers": {
                "Authorization": f"Bearer {client_secret}",
                "Content-Type": "application/json"
            }
        },
        {
            "name": "Bearer with Client Secret + X-Client-Id header",
            "headers": {
                "Authorization": f"Bearer {client_secret}",
                "X-Client-Id": client_id,
                "Content-Type": "application/json"
            }
        },
        {
            "name": "Basic Auth with Client ID:Secret",
            "headers": {
                "Authorization": f"Basic {requests.auth._basic_auth_str(client_id, client_secret)}",
                "Content-Type": "application/json"
            }
        }
    ]
    
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
    
    for method in auth_methods:
        print(f"\n{'='*60}")
        print(f"Trying: {method['name']}")
        print(f"{'='*60}")
        
        try:
            response = requests.post(
                f"{base_url}/payments",
                headers=method['headers'],
                json=payload,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            try:
                response_json = response.json()
                print(f"Response: {json.dumps(response_json, indent=2)}")
                
                if response.status_code == 200 or response.status_code == 201:
                    print(f"\n✅ SUCCESS with method: {method['name']}")
                    return method['headers']
                elif response.status_code == 401:
                    print(f"❌ Authentication failed")
                else:
                    print(f"❌ Error: {response.status_code}")
            except:
                print(f"Response text: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
    
    print(f"\n{'='*60}")
    print("None of the authentication methods worked.")
    print("Please check Flutterwave v4 API documentation for correct auth format.")
    print(f"{'='*60}")
    return None

if __name__ == "__main__":
    test_flutterwave_v4()

