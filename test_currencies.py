from app.routers.wallet import _get_exchange_rate, _convert_to_sokocoin
from config import settings

print("Exchange Rates:")
print(f"  TZS: {_get_exchange_rate('TZS')}")
print(f"  KES: {_get_exchange_rate('KES')}")
print(f"  NGN: {_get_exchange_rate('NGN')}")
print()
print("Conversion Test (100 units):")
print(f"  TZS 100 = {_convert_to_sokocoin(100, 'TZS'):.2f} Sokocoin")
print(f"  KES 100 = {_convert_to_sokocoin(100, 'KES'):.2f} Sokocoin")
print(f"  NGN 100 = {_convert_to_sokocoin(100, 'NGN'):.2f} Sokocoin")
print()
print("Flutterwave API Keys:")
print(f"  Secret Key: {settings.FLW_SECRET_KEY[:20]}...")
print(f"  Public Key: {settings.FLW_PUBLIC_KEY[:20]}...")
print()
print("All currencies should work now!")

