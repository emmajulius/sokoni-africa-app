"""
Quick test script to verify OTP endpoint is working
Run this while your backend is running to test OTP functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_send_otp(phone_number):
    """Test sending OTP"""
    url = f"{BASE_URL}/api/auth/send-otp"
    payload = {"phone": phone_number}
    
    print(f"\n{'='*60}")
    print(f"Testing OTP endpoint: {url}")
    print(f"Phone number: {phone_number}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ OTP sent successfully!")
            print("Check your backend console/terminal for the OTP code")
            print("(In development mode, OTP is printed to console)")
        else:
            print(f"\n❌ Error: {response.text}")
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend!")
        print("Make sure your backend is running:")
        print("  cd sokoni_africa_app\\africa_sokoni_app_backend")
        print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Test with a sample phone number
    test_phone = input("Enter phone number to test (e.g., +255123456789): ").strip()
    if not test_phone:
        test_phone = "+255123456789"  # Default test number
    
    test_send_otp(test_phone)

