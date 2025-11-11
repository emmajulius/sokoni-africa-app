from config import settings

sk = settings.FLW_SECRET_KEY
print("Current FLW_SECRET_KEY format:")
print(f"  Value: {sk[:30]}...")
print(f"  Starts with FLWSECK: {sk.startswith('FLWSECK')}")
print(f"  Starts with FLWSECK_TEST: {sk.startswith('FLWSECK_TEST')}")
print(f"  Length: {len(sk)}")
print()
print("NOTE: Flutterwave API requires Secret Key (FLWSECK_TEST-xxx format)")
print("      Client Secret from dashboard cannot be used directly for API calls")

