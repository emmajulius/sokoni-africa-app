import requests
import json
from typing import Optional, Dict, Any
from config import settings
from datetime import datetime


class FlutterwaveService:
    """Service for interacting with Flutterwave payment gateway"""
    
    def __init__(self):
        self.secret_key = settings.FLW_SECRET_KEY  # Secret Key (FLWSECK_TEST-...)
        self.public_key = settings.FLW_PUBLIC_KEY  # Public Key (FLWPUBK_TEST-...)
        self.encryption_key = settings.FLW_ENCRYPTION_KEY
        self.base_url = settings.FLUTTERWAVE_BASE_URL
        
        # For Flutterwave API v3, use Secret Key as Bearer token
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        # Store as client_id and client_secret for reference
        self.client_id = self.public_key
        self.client_secret = self.secret_key
    
    def initialize_payment(
        self,
        amount: float,
        currency: str,
        email: str,
        tx_ref: str,
        customer_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        payment_method: str = "card",
        redirect_url: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initialize a payment transaction
        
        Args:
            amount: Amount to charge
            currency: Currency code (TZS, KES, NGN, etc.)
            email: Customer email
            tx_ref: Unique transaction reference
            customer_name: Customer full name
            phone_number: Customer phone number
            payment_method: Payment method (card, mobile_money, bank_transfer)
            redirect_url: URL to redirect after payment
            meta: Additional metadata
        
        Returns:
            Dict containing payment initialization response
        """
        currency_upper = (currency or "").upper()

        def build_payment_options() -> str:
            if payment_method == "card":
                return "card"
            if payment_method == "bank_transfer":
                return "banktransfer"
            if payment_method == "mobile_money":
                if currency_upper == "KES":
                    return "mpesa,card"
                if currency_upper == "TZS":
                    return "mobilemoneytanzania,card"
                if currency_upper == "UGX":
                    return "mobilemoneyuganda,card"
                if currency_upper == "RWF":
                    return "mobilemoneyrwanda,card"
                if currency_upper == "ZMW":
                    return "mobilemoneyzambia,card"
                if currency_upper == "GHS":
                    return "mobilemoneyghana,card"
                if currency_upper == "NGN":
                    return "ussd,banktransfer,card"
                return "mobilemoney,card"
            return "card"

        payment_option = build_payment_options()
        
        payload = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": currency,
            "payment_options": payment_option,
            "redirect_url": redirect_url or f"{settings.FLUTTERWAVE_BASE_URL}/payment/callback",
            "customer": {
                "email": email,
                "name": customer_name or "Customer",
                "phone_number": phone_number,
                "country": self._map_currency_to_country(currency_upper)
            },
            "meta": meta or {}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/payments",
                headers=self.headers,
                json=payload,
                timeout=20
            )
            print(f"[DEBUG] Flutterwave API Response:")
            print(f"  Status Code: {response.status_code}")
            print(f"  Response: {response.text[:500]}")  # First 500 chars
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200] if e.response else str(e)}"
            print(f"[ERROR] Flutterwave API HTTP Error: {error_detail}")
            raise Exception(f"Flutterwave API error: {error_detail}")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Flutterwave API Request Error: {str(e)}")
            raise Exception(f"Flutterwave API error: {str(e)}")
    
    def verify_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verify a transaction status
        
        Args:
            transaction_id: Flutterwave transaction ID
        
        Returns:
            Dict containing transaction details
        """
        try:
            response = requests.get(
                f"{self.base_url}/transactions/{transaction_id}/verify",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Flutterwave API error: {str(e)}")
    
    def initiate_transfer(
        self,
        account_bank: str,
        account_number: str,
        amount: float,
        currency: str,
        narration: str,
        beneficiary_name: Optional[str] = None,
        reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate a bank transfer (for cashout)
        
        Args:
            account_bank: Bank code
            account_number: Account number
            amount: Amount to transfer
            currency: Currency code
            narration: Transfer description
            beneficiary_name: Beneficiary name
            reference: Unique reference
        
        Returns:
            Dict containing transfer response
        """
        payload = {
            "account_bank": account_bank,
            "account_number": account_number,
            "amount": amount,
            "currency": currency,
            "narration": narration,
            "beneficiary_name": beneficiary_name or "Sokoni User",
            "reference": reference or f"SOKONI_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/transfers",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            if response.status_code >= 400:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass
                
                error_message = error_data.get("message", response.text[:200])
                error_code = error_data.get("code", "")
                
                # Check for IP whitelist error
                if "IP" in error_message and ("whitelist" in error_message.lower() or "Whitelisting" in error_message):
                    raise Exception("IP Whitelisting: Please enable IP whitelisting to access this service")
                
                raise Exception(f"Flutterwave API error ({response.status_code}): {error_message}")
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception("Request timeout: Flutterwave API took too long to respond")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Flutterwave API error: {str(e)}")
    
    def initiate_mobile_money_transfer(
        self,
        phone_number: str,
        amount: float,
        currency: str,
        narration: str,
        provider: str = "MPESA",  # MPESA, MTN, Airtel, etc.
        reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initiate a mobile money transfer (for cashout)
        
        Args:
            phone_number: Mobile money phone number
            amount: Amount to transfer
            currency: Currency code
            narration: Transfer description
            provider: Mobile money provider
            reference: Unique reference
        
        Returns:
            Dict containing transfer response
        """
        currency_upper = (currency or "").upper()
        provider_map = {
            "KES": "MPESA",
            "TZS": "TANZANIA",
            "UGX": "UGANDA",
            "RWF": "RWANDA",
            "ZMW": "ZAMBIA",
            "GHS": "GHANA",
        }

        payload = {
            "account_bank": provider_map.get(currency_upper, provider),
            "account_number": phone_number,
            "amount": amount,
            "currency": currency_upper,
            "debit_currency": currency_upper,
            "narration": narration,
            "reference": reference or f"SOKONI_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/transfers",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            if response.status_code >= 400:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass
                
                error_message = error_data.get("message", response.text[:200])
                error_code = error_data.get("code", "")
                
                # Check for IP whitelist error
                if "IP" in error_message and ("whitelist" in error_message.lower() or "Whitelisting" in error_message):
                    raise Exception("IP Whitelisting: Please enable IP whitelisting to access this service")
                
                raise Exception(f"Flutterwave API error ({response.status_code}): {error_message}")
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception("Request timeout: Flutterwave API took too long to respond")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Flutterwave API error: {str(e)}")
    
    def get_banks(self, country: str = "NG") -> Dict[str, Any]:
        """
        Get list of banks for a country
        
        Args:
            country: Country code (NG, KE, TZ, etc.)
        
        Returns:
            Dict containing list of banks
        """
        try:
            response = requests.get(
                f"{self.base_url}/banks/{country}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Flutterwave API error: {str(e)}")

    @staticmethod
    def _map_currency_to_country(currency: str) -> str:
        mapping = {
            "KES": "KE",
            "TZS": "TZ",
            "NGN": "NG",
            "UGX": "UG",
            "RWF": "RW",
            "ZMW": "ZM",
            "GHS": "GH",
            "USD": "US",
        }
        return mapping.get(currency.upper(), "NG")

