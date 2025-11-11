"""
Direct test of Flutterwave API call
This will help us see the exact error from Flutterwave
"""
import requests
import json
from config import settings

def test_flutterwave_api():
    print("=" * 60)
    print("Testing Flutterwave API Direct Call")
    print("=" * 60)
    print()
    
    # Get credentials
    client_secret = settings.FLW_SECRET_KEY
    client_id = settings.FLW_PUBLIC_KEY
    base_url = settings.FLUTTERWAVE_BASE_URL
    
    print(f"Client ID: {client_id[:20]}...")
    print(f"Client Secret: {client_secret[:20]}...")
    print(f"Base URL: {base_url}")
    print()
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {client_secret}",
        "Content-Type": "application/json"
    }
    
    # Test payload (minimal)
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
    
    print("Request Details:")
    print(f"  URL: {base_url}/payments")
    print(f"  Method: POST")
    print(f"  Headers: Authorization: Bearer {client_secret[:20]}...")
    print(f"  Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        print("Making API call...")
        response = requests.post(
            f"{base_url}/payments",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print()
        print("=" * 60)
        print("Response:")
        print("=" * 60)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print()
        print("Response Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
        except:
            print(response.text)
        
        print()
        print("=" * 60)
        
        if response.status_code == 200 or response.status_code == 201:
            print("✅ SUCCESS: API call was successful!")
        else:
            print(f"❌ ERROR: API returned status {response.status_code}")
            if response.status_code == 401:
                print("   This indicates authentication failure - check your Client Secret")
            elif response.status_code == 403:
                print("   This indicates authorization failure - check your API permissions")
            elif response.status_code == 400:
                print("   This indicates bad request - check your payload format")
        
    except requests.exceptions.RequestException as e:
        print()
        print("=" * 60)
        print("❌ REQUEST ERROR:")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print(f"Type: {type(e).__name__}")

if __name__ == "__main__":
    test_flutterwave_api()

