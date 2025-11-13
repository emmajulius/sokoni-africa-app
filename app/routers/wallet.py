from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from database import get_db
from models import User, Wallet, WalletTransaction, WalletTransactionType, WalletTransactionStatus, Notification
from schemas import (
    WalletResponse,
    WalletTransactionResponse,
    TopupCreate,
    CashoutCreate,
    FlutterwaveWebhookData
)
from auth import get_current_user, get_current_active_user
from flutterwave_service import FlutterwaveService
from config import settings
import uuid
import re

router = APIRouter(prefix="/wallet", tags=["wallet"])
flutterwave_service = FlutterwaveService()


def _get_callback_url(request: Request) -> str:
    """
    Get the callback URL for Flutterwave payment redirect.
    Uses the request's host if it's a valid IP address (for mobile devices),
    otherwise falls back to APP_BASE_URL from settings.
    """
    # Get the base URL from settings
    base_url = settings.APP_BASE_URL
    
    # Get host from Host header (most reliable)
    host_header = request.headers.get("host", "")
    # Remove port from host header if present (e.g., "192.168.1.186:8000" -> "192.168.1.186")
    host = host_header.split(":")[0] if host_header else ""
    
    # Get port from request URL or host header
    port = request.url.port
    if not port:
        # Try to extract port from host header
        if ":" in host_header:
            try:
                port = int(host_header.split(":")[1])
            except (ValueError, IndexError):
                port = 80 if request.url.scheme == "http" else 443
        else:
            port = 80 if request.url.scheme == "http" else 443
    
    scheme = request.url.scheme
    
    # Check if host is a valid IP address (e.g., 192.168.x.x, 10.x.x.x, etc.)
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    is_ip = re.match(ip_pattern, host) if host else False
    
    # Check if host is localhost or 127.0.0.1
    is_localhost = host.lower() in ["localhost", "127.0.0.1", "0.0.0.0", ""]
    
    # If we have a valid IP address (not localhost), use it for the callback URL
    # This ensures mobile devices can reach the callback URL
    if is_ip and not is_localhost:
        if port not in [80, 443]:
            callback_url = f"{scheme}://{host}:{port}/api/wallet/topup/callback"
        else:
            callback_url = f"{scheme}://{host}/api/wallet/topup/callback"
        print(f"[CALLBACK URL] Using request host IP: {callback_url}")
        return callback_url
    
    # If APP_BASE_URL contains localhost, check if we can use the request host
    if "localhost" in base_url.lower() or "127.0.0.1" in base_url:
        if is_ip and host:
            if port not in [80, 443]:
                callback_url = f"{scheme}://{host}:{port}/api/wallet/topup/callback"
            else:
                callback_url = f"{scheme}://{host}/api/wallet/topup/callback"
            print(f"[CALLBACK URL] Replaced localhost with request host IP: {callback_url}")
            return callback_url
        else:
            # If we can't get a valid IP from request, warn and use APP_BASE_URL
            print(f"[CALLBACK URL WARNING] APP_BASE_URL uses localhost but request host is '{host}'. "
                  f"Mobile devices may not be able to reach the callback URL. "
                  f"Consider setting APP_BASE_URL to your LAN IP (e.g., http://192.168.1.186:8000) in .env")
    
    # Fall back to APP_BASE_URL from settings
    callback_url = f"{base_url}/api/wallet/topup/callback"
    print(f"[CALLBACK URL] Using APP_BASE_URL from settings: {callback_url}")
    return callback_url


@router.get("/topup/callback", response_class=HTMLResponse)
async def flutterwave_topup_callback(
    status: str = Query(None),
    tx_ref: str = Query(None, alias="tx_ref"),
    transaction_id: str = Query(None, alias="transaction_id"),
    flw_ref: str = Query(None, alias="flw_ref"),
    message: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle Flutterwave redirect callback without requiring user authentication"""
    status_lower = (status or "").lower()
    page_title = "Payment Status"
    description = message or ""

    transaction = None
    if tx_ref:
        transaction = db.query(WalletTransaction).filter(
            WalletTransaction.payment_reference == tx_ref
        ).first()

    if not transaction:
        html_content = f"""
            <html>
              <head>
                <title>{page_title}</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                  body {{ font-family: Arial, sans-serif; background-color: #f7f7f7; color: #333; text-align: center; padding: 20px; margin: 0; }}
                  .card {{ background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 460px; margin: 40px auto; }}
                  .status-icon {{ font-size: 72px; color: #f44336; margin-bottom: 20px; }}
                  h1 {{ color: #f44336; margin: 20px 0; }}
                  p {{ color: #666; line-height: 1.6; margin: 10px 0; }}
                  .instructions {{ background: #ffebee; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left; }}
                  .instructions h3 {{ margin-top: 0; color: #f44336; }}
                  .instructions ol {{ margin: 10px 0; padding-left: 20px; }}
                  .instructions li {{ margin: 8px 0; color: #555; }}
                </style>
              </head>
              <body>
                <div class="card">
                  <div class="status-icon">⚠️</div>
                  <h1>Transaction Not Found</h1>
                  <p>We could not locate the payment reference <strong>{tx_ref or 'N/A'}</strong>.</p>
                  <div class="instructions">
                    <h3>What to do:</h3>
                    <ol>
                      <li>Close this browser tab/window</li>
                      <li>Return to the Sokoni app</li>
                      <li>Go to your Wallet screen</li>
                      <li>Check your transaction history</li>
                      <li>Contact support if payment was deducted</li>
                    </ol>
                  </div>
                  <p style="color: #999; font-size: 14px; margin-top: 20px;">You can safely close this page now.</p>
                </div>
              </body>
            </html>
        """
        return HTMLResponse(content=html_content)

    if status_lower == "successful":
        verification_id = transaction_id or flw_ref or transaction.gateway_transaction_id
        try:
            if verification_id:
                verification = flutterwave_service.verify_transaction(str(verification_id))
            else:
                verification = {"status": "success", "data": {"status": "successful"}}

            verification_status = verification.get("status")
            verification_data = verification.get("data", {})

            if verification_status == "success" and verification_data.get("status") == "successful":
                if transaction.status != WalletTransactionStatus.COMPLETED:
                    transaction.status = WalletTransactionStatus.COMPLETED
                    transaction.completed_at = datetime.now(timezone.utc)

                    wallet = transaction.wallet
                    wallet.sokocoin_balance += transaction.sokocoin_amount
                    wallet.total_topup += transaction.local_currency_amount or 0

                    notification = Notification(
                        user_id=transaction.user_id,
                        notification_type="wallet",
                        title="Top-up Successful",
                        message=f"You have successfully topped up {transaction.sokocoin_amount:.2f} Sokocoin",
                        is_read=False
                    )
                    db.add(notification)
                    db.commit()

                page_title = "Payment Successful"
                html_content = f"""
                    <html>
                      <head>
                        <title>{page_title}</title>
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <style>
                          body {{ font-family: Arial, sans-serif; background-color: #f7f7f7; color: #333; text-align: center; padding: 20px; margin: 0; }}
                          .card {{ background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 460px; margin: 40px auto; }}
                          .status-icon {{ font-size: 72px; color: #2e7d32; margin-bottom: 20px; }}
                          h1 {{ color: #2e7d32; margin: 20px 0; }}
                          p {{ color: #666; line-height: 1.6; margin: 10px 0; }}
                          .instructions {{ background: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left; }}
                          .instructions h3 {{ margin-top: 0; color: #2e7d32; }}
                          .instructions ol {{ margin: 10px 0; padding-left: 20px; }}
                          .instructions li {{ margin: 8px 0; color: #555; }}
                        </style>
                      </head>
                      <body>
                        <div class="card">
                          <div class="status-icon">✅</div>
                          <h1>Payment Successful!</h1>
                          <p><strong>Your payment has been received and processed.</strong></p>
                          <div class="instructions">
                            <h3>Next Steps:</h3>
                            <ol>
                              <li>Close this browser tab/window</li>
                              <li>Return to the Sokoni app</li>
                              <li>Go to your Wallet screen</li>
                              <li>Click "Verify Payment" if needed</li>
                              <li>Your wallet balance will be updated</li>
                            </ol>
                          </div>
                          <p style="color: #999; font-size: 14px; margin-top: 20px;">You can safely close this page now.</p>
                        </div>
                      </body>
                    </html>
                """
                return HTMLResponse(content=html_content)
        except Exception as exc:
            description = f"Verification error: {str(exc)}"

    if status_lower == "cancelled":
        transaction.status = WalletTransactionStatus.CANCELLED
        db.commit()
        page_title = "Payment Cancelled"
        description = description or "You cancelled the payment."
        icon = "⚠️"
        color = "#f57c00"
    else:
        if status_lower and status_lower != "successful":
            transaction.status = WalletTransactionStatus.FAILED
            db.commit()
        page_title = "Payment Pending"
        icon = "⏳"
        color = "#1976d2"
        if not description:
            description = "Your payment is still processing. Please return to the Sokoni app and verify from the wallet screen."

    html_content = f"""
        <html>
          <head>
            <title>{page_title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
              body {{ font-family: Arial, sans-serif; background-color: #f7f7f7; color: #333; text-align: center; padding: 20px; margin: 0; }}
              .card {{ background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 460px; margin: 40px auto; }}
              .status-icon {{ font-size: 72px; color: {color}; margin-bottom: 20px; }}
              h1 {{ color: {color}; margin: 20px 0; }}
              p {{ color: #666; line-height: 1.6; margin: 10px 0; }}
              .instructions {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left; }}
              .instructions h3 {{ margin-top: 0; color: {color}; }}
              .instructions ol {{ margin: 10px 0; padding-left: 20px; }}
              .instructions li {{ margin: 8px 0; color: #555; }}
            </style>
          </head>
          <body>
            <div class="card">
              <div class="status-icon">{icon}</div>
              <h1>{page_title}</h1>
              <p>{description}</p>
              <div class="instructions">
                <h3>What to do:</h3>
                <ol>
                  <li>Close this browser tab/window</li>
                  <li>Return to the Sokoni app</li>
                  <li>Go to your Wallet screen</li>
                  <li>Check your transaction status</li>
                </ol>
              </div>
              <p style="color: #999; font-size: 14px; margin-top: 20px;">You can safely close this page now.</p>
            </div>
          </body>
        </html>
    """
    return HTMLResponse(content=html_content)



def _get_or_create_wallet(user_id: int, db: Session) -> Wallet:
    """Get or create a wallet for a user"""
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


def _get_exchange_rate(currency: str) -> float:
    """Get exchange rate for converting local currency to Sokocoin"""
    currency_upper = currency.upper()
    if currency_upper == "TZS":
        return settings.SOKOCOIN_EXCHANGE_RATE_TZS
    elif currency_upper == "KES":
        return settings.SOKOCOIN_EXCHANGE_RATE_KES
    elif currency_upper == "NGN":
        return settings.SOKOCOIN_EXCHANGE_RATE_NGN
    else:
        # Default to 1:1 for unknown currencies
        return 1.0


def _convert_to_sokocoin(local_amount: float, currency: str) -> float:
    """Convert local currency amount to Sokocoin
    Exchange rate is defined as: 1 Sokocoin = X local currency
    So to convert local currency to Sokocoin: local_amount / exchange_rate
    """
    exchange_rate = _get_exchange_rate(currency)
    if exchange_rate <= 0:
        return 0.0
    return local_amount / exchange_rate


def _convert_from_sokocoin(sokocoin_amount: float, currency: str) -> float:
    """Convert Sokocoin amount to local currency
    Exchange rate is defined as: 1 Sokocoin = X local currency
    So to convert Sokocoin to local currency: sokocoin_amount * exchange_rate
    """
    exchange_rate = _get_exchange_rate(currency)
    return sokocoin_amount * exchange_rate if exchange_rate > 0 else 0.0


@router.get("/balance", response_model=WalletResponse)
async def get_wallet_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's wallet balance"""
    wallet = _get_or_create_wallet(current_user.id, db)
    return wallet


@router.get("/transactions", response_model=List[WalletTransactionResponse])
async def get_wallet_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    transaction_type: Optional[WalletTransactionType] = None,
    status: Optional[WalletTransactionStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get wallet transaction history"""
    wallet = _get_or_create_wallet(current_user.id, db)
    
    query = db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id == wallet.id
    )
    
    if transaction_type:
        query = query.filter(WalletTransaction.transaction_type == transaction_type)
    
    if status:
        query = query.filter(WalletTransaction.status == status)
    
    transactions = query.order_by(desc(WalletTransaction.created_at)).offset(skip).limit(limit).all()
    return transactions


@router.post("/topup/initialize")
async def initialize_topup(
    topup_data: TopupCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize a top-up transaction"""
    wallet = _get_or_create_wallet(current_user.id, db)
    
    # Convert local currency to Sokocoin
    sokocoin_amount = _convert_to_sokocoin(topup_data.amount, topup_data.currency)
    exchange_rate = _get_exchange_rate(topup_data.currency)

    phone_number = (topup_data.phone_number or current_user.phone or "").strip()
    if topup_data.payment_method == "mobile_money" and not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required for mobile money payments"
        )
    
    # Generate unique transaction reference
    tx_ref = f"SOKONI_TOPUP_{current_user.id}_{uuid.uuid4().hex[:12]}"
    
    # Create pending transaction
    transaction = WalletTransaction(
        wallet_id=wallet.id,
        user_id=current_user.id,
        transaction_type=WalletTransactionType.TOPUP,
        status=WalletTransactionStatus.PENDING,
        sokocoin_amount=sokocoin_amount,
        local_currency_amount=topup_data.amount,
        local_currency_code=topup_data.currency,
        exchange_rate=exchange_rate,
        payment_gateway="flutterwave",
        payment_reference=tx_ref,
        description=f"Top-up {topup_data.amount} {topup_data.currency}"
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    # Determine whether to skip real gateway and use sandbox behaviour
    secret_key = (settings.FLW_SECRET_KEY or "").strip()
    public_key = (settings.FLW_PUBLIC_KEY or "").strip()

    if settings.MOCK_FLUTTERWAVE_TOPUPS:
        transaction.status = WalletTransactionStatus.COMPLETED
        transaction.completed_at = datetime.now(timezone.utc)

        wallet.sokocoin_balance += transaction.sokocoin_amount
        wallet.total_topup += transaction.local_currency_amount or 0

        notification = Notification(
            user_id=current_user.id,
            notification_type="wallet",
            title="Top-up Successful",
            message=(
                f"You have received {transaction.sokocoin_amount:.2f} Sokocoin "
                f"({topup_data.amount:.2f} {topup_data.currency})"
            ),
            is_read=False
        )
        db.add(notification)
        db.commit()

        return {
            "success": True,
            "transaction_id": transaction.id,
            "payment_url": None,
            "payment_reference": tx_ref,
            "sokocoin_amount": sokocoin_amount,
            "local_amount": topup_data.amount,
            "currency": topup_data.currency,
            "message": "Test mode: wallet credited without contacting Flutterwave."
        }

    if not secret_key or not public_key:
        transaction.status = WalletTransactionStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Flutterwave API keys are not configured. Set FLW_PUBLIC_KEY and FLW_SECRET_KEY in the backend environment, or enable MOCK_FLUTTERWAVE_TOPUPS."
        )

    # Initialize Flutterwave payment
    try:
        # Reinitialize service to ensure latest config is used
        fw_service = FlutterwaveService()
        
        print(f"[DEBUG] FlutterwaveService initialized:")
        print(f"  Service Secret Key: {'SET' if fw_service.secret_key else 'NOT SET'}")
        print(f"  Service Public Key: {'SET' if fw_service.public_key else 'NOT SET'}")
        
        # Get the callback URL - use request host for mobile devices
        callback_url = _get_callback_url(request)
        
        payment_response = fw_service.initialize_payment(
            amount=topup_data.amount,
            currency=topup_data.currency,
            email=current_user.email or f"{current_user.username}@sokoni.app",
            tx_ref=tx_ref,
            customer_name=current_user.full_name,
            phone_number=phone_number or None,
            payment_method=topup_data.payment_method,
            redirect_url=callback_url,
            meta={
                "transaction_id": transaction.id,
                "user_id": current_user.id,
                "sokocoin_amount": sokocoin_amount
            }
        )
        
        # Update transaction with gateway transaction ID if available
        if payment_response.get("status") == "success":
            data = payment_response.get("data", {})
            transaction.gateway_transaction_id = data.get("id")
            db.commit()
            
            return {
                "success": True,
                "transaction_id": transaction.id,
                "payment_url": data.get("link"),
                "payment_reference": tx_ref,
                "sokocoin_amount": sokocoin_amount,
                "local_amount": topup_data.amount,
                "currency": topup_data.currency
            }
        else:
            transaction.status = WalletTransactionStatus.FAILED
            db.commit()
            error_message = payment_response.get("message", "Failed to initialize payment")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment initialization failed: {error_message}"
            )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        transaction.status = WalletTransactionStatus.FAILED
        db.commit()
        error_msg = str(e)
        # Provide user-friendly error messages
        if "API error" in error_msg or "401" in error_msg or "403" in error_msg:
            error_msg = "Flutterwave API authentication failed. Please check API keys configuration."
        elif "Connection" in error_msg or "timeout" in error_msg.lower():
            error_msg = "Unable to connect to payment gateway. Please try again later."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization error: {error_msg}"
        )


@router.post("/topup/verify/{transaction_id}")
async def verify_topup(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify a top-up transaction"""
    # Refresh transaction from database to get latest status
    db.expire_all()
    transaction = db.query(WalletTransaction).filter(
        WalletTransaction.id == transaction_id,
        WalletTransaction.user_id == current_user.id,
        WalletTransaction.transaction_type == WalletTransactionType.TOPUP
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # If transaction is already completed (e.g., by callback), return success immediately
    if transaction.status == WalletTransactionStatus.COMPLETED:
        return {
            "success": True,
            "message": "Transaction already completed",
            "transaction": transaction
        }
    
    # Verify with Flutterwave if we have a gateway transaction ID
    if transaction.gateway_transaction_id:
        try:
            verification = flutterwave_service.verify_transaction(transaction.gateway_transaction_id)
            
            if verification.get("status") == "success":
                data = verification.get("data", {})
                payment_status = data.get("status", "").lower()
                
                if payment_status == "successful":
                    # Double-check transaction status hasn't changed (race condition protection)
                    db.refresh(transaction)
                    if transaction.status == WalletTransactionStatus.COMPLETED:
                        # Already processed by callback
                        return {
                            "success": True,
                            "message": "Transaction already completed",
                            "transaction": transaction
                        }
                    
                    # Only update if status is still PENDING (prevents double processing)
                    if transaction.status == WalletTransactionStatus.PENDING:
                        # Update transaction status
                        transaction.status = WalletTransactionStatus.COMPLETED
                        transaction.completed_at = datetime.now(timezone.utc)
                        
                        # Update wallet balance
                        wallet = transaction.wallet
                        db.refresh(wallet)
                        wallet.sokocoin_balance += transaction.sokocoin_amount
                        wallet.total_topup = (wallet.total_topup or 0) + (transaction.local_currency_amount or 0)
                        
                        # Create notification
                        notification = Notification(
                            user_id=current_user.id,
                            notification_type="wallet",
                            title="Top-up Successful",
                            message=f"You have successfully topped up {transaction.sokocoin_amount:.2f} Sokocoin",
                            is_read=False
                        )
                        db.add(notification)
                        db.commit()
                        
                        return {
                            "success": True,
                            "message": "Top-up verified and completed",
                            "transaction": transaction
                        }
                    else:
                        # Transaction status changed (possibly by callback) - refresh and return
                        db.refresh(transaction)
                        return {
                            "success": transaction.status == WalletTransactionStatus.COMPLETED,
                            "message": f"Transaction status: {transaction.status.value}",
                            "transaction": transaction
                        }
                elif payment_status in ["pending", "processing"]:
                    # Payment is still processing, return pending status
                    return {
                        "success": False,
                        "message": "Payment is still processing. Please wait a moment and try again.",
                        "transaction": transaction
                    }
                else:
                    # Payment failed or cancelled
                    transaction.status = WalletTransactionStatus.FAILED
                    db.commit()
                    return {
                        "success": False,
                        "message": f"Payment not successful. Status: {payment_status}",
                        "transaction": transaction
                    }
            else:
                # Flutterwave verification returned an error
                error_message = verification.get("message", "Verification failed")
                return {
                    "success": False,
                    "message": f"Verification failed: {error_message}",
                    "transaction": transaction
                }
        except Exception as e:
            # Log the error but don't fail completely - transaction might still be processing
            import traceback
            print(f"Error verifying transaction {transaction_id}: {str(e)}")
            print(traceback.format_exc())
            
            # Check if transaction was completed by callback while we were verifying
            db.refresh(transaction)
            if transaction.status == WalletTransactionStatus.COMPLETED:
                return {
                    "success": True,
                    "message": "Transaction completed",
                    "transaction": transaction
                }
            
            # Return pending status so client can retry
            return {
                "success": False,
                "message": f"Verification error: {str(e)}. Transaction may still be processing.",
                "transaction": transaction
            }
    
    # No gateway transaction ID - transaction might be pending initialization
    return {
        "success": False,
        "message": "Transaction pending verification. Please wait a moment and try again.",
        "transaction": transaction
    }


def _normalize_mobile_money_number(phone: str, currency: str) -> str:
    phone_clean = phone.replace(" ", "").replace("-", "")
    if not phone_clean:
        raise ValueError("Phone number is required for mobile money")

    if not phone_clean.startswith("+"):
        raise ValueError("Provide the phone number in international format, e.g. +2557XXXXXXXX")

    currency_upper = currency.upper()

    if currency_upper == "TZS" and not phone_clean.startswith("+255"):
        raise ValueError("Tanzania mobile money number must start with +255")

    if currency_upper == "KES" and not phone_clean.startswith("+254"):
        raise ValueError("Kenya mobile money number must start with +254")

    if len(phone_clean) < 10:
        raise ValueError("Phone number is too short. Include full international number, e.g. +2557XXXXXXXX")

    return phone_clean


@router.post("/cashout")
async def initiate_cashout(
    cashout_data: CashoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate a cashout transaction"""
    wallet = _get_or_create_wallet(current_user.id, db)
    
    # Check if user has sufficient balance
    if wallet.sokocoin_balance < cashout_data.sokocoin_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient Sokocoin balance"
        )
    
    # Convert Sokocoin to local currency
    local_amount = _convert_from_sokocoin(cashout_data.sokocoin_amount, cashout_data.currency)
    exchange_rate = _get_exchange_rate(cashout_data.currency)
    
    # Generate unique reference
    reference = f"SOKONI_CASHOUT_{current_user.id}_{uuid.uuid4().hex[:12]}"
    
    # Create pending transaction (do not deduct balance yet)
    transaction = WalletTransaction(
        wallet_id=wallet.id,
        user_id=current_user.id,
        transaction_type=WalletTransactionType.CASHOUT,
        status=WalletTransactionStatus.PENDING,
        sokocoin_amount=cashout_data.sokocoin_amount,
        local_currency_amount=local_amount,
        local_currency_code=cashout_data.currency,
        exchange_rate=exchange_rate,
        payment_gateway="flutterwave",
        payout_method=cashout_data.payout_method,
        payout_account=cashout_data.payout_account,
        payout_reference=reference,
        description=f"Cashout {cashout_data.sokocoin_amount} Sokocoin"
    )
    db.add(transaction)
    db.flush()
    db.refresh(transaction)

    secret_key = settings.FLW_SECRET_KEY or ""
    use_mock_transfer = settings.MOCK_CASHOUT_TRANSFERS or secret_key.startswith("FLWSECK_TEST")

    if use_mock_transfer:
        transaction.status = WalletTransactionStatus.COMPLETED
        transaction.completed_at = datetime.now(timezone.utc)

        wallet.sokocoin_balance -= cashout_data.sokocoin_amount
        wallet.total_cashout = (wallet.total_cashout or 0) + local_amount

        notification = Notification(
            user_id=current_user.id,
            notification_type="wallet",
            title="Cashout Initiated",
            message=f"Your cashout of {cashout_data.sokocoin_amount:.2f} Sokocoin has been initiated (sandbox).",
            is_read=False
        )
        db.add(notification)
        db.commit()

        return {
            "success": True,
            "message": "Cashout simulated successfully",
            "transaction": transaction
        }
    
    # Normalize payout account based on method
    payout_account = cashout_data.payout_account.strip()
    currency_upper = cashout_data.currency.upper()

    if cashout_data.payout_method == "mobile_money":
        try:
            payout_account = _normalize_mobile_money_number(payout_account, currency_upper)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Initiate Flutterwave transfer
    try:
        if cashout_data.payout_method == "mobile_money":
            transfer_response = flutterwave_service.initiate_mobile_money_transfer(
                phone_number=payout_account,
                amount=local_amount,
                currency=cashout_data.currency,
                narration=f"Sokocoin cashout - {cashout_data.sokocoin_amount} Sokocoin",
                reference=reference
            )
        else:
            # Bank transfer
            transfer_response = flutterwave_service.initiate_transfer(
                account_bank=cashout_data.bank_name or "058",
                account_number=payout_account,
                amount=local_amount,
                currency=cashout_data.currency,
                narration=f"Sokocoin cashout - {cashout_data.sokocoin_amount} Sokocoin",
                beneficiary_name=cashout_data.account_name or current_user.full_name,
                reference=reference
            )
        
        if transfer_response.get("status") == "success":
            data = transfer_response.get("data", {})
            transaction.gateway_transaction_id = data.get("id")
            transaction.status = WalletTransactionStatus.COMPLETED
            transaction.completed_at = datetime.now(timezone.utc)

            # Deduct balance only after we are sure the transfer succeeded
            wallet.sokocoin_balance -= cashout_data.sokocoin_amount
            wallet.total_cashout = (wallet.total_cashout or 0) + local_amount

            notification = Notification(
                user_id=current_user.id,
                notification_type="wallet",
                title="Cashout Initiated",
                message=f"Your cashout of {cashout_data.sokocoin_amount:.2f} Sokocoin has been initiated",
                is_read=False
            )
            db.add(notification)
            db.commit()
            
            return {
                "success": True,
                "message": "Cashout initiated successfully",
                "transaction": transaction
            }
        else:
            transaction.status = WalletTransactionStatus.FAILED
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to initiate cashout"
            )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # Validation errors from phone number normalization
        transaction.status = WalletTransactionStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        transaction.status = WalletTransactionStatus.FAILED
        db.commit()
        error_message = str(e)

        # Handle specific Flutterwave errors
        if "IP Whitelist" in error_message or "IP Whitelisting" in error_message:
            detail = (
                "Flutterwave rejected the transfer because the server IP is not whitelisted. "
                "Add your backend server's public IP address to the IP whitelist in the Flutterwave dashboard "
                "or set MOCK_CASHOUT_TRANSFERS=true in the backend .env for sandbox testing."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail
            )
        elif "timeout" in error_message.lower():
            detail = (
                "The transfer request timed out. Please check your internet connection and try again. "
                "If the issue persists, contact support."
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=detail
            )
        elif "401" in error_message or "403" in error_message or "authentication" in error_message.lower():
            detail = (
                "Flutterwave API authentication failed. Please check your API keys in the backend .env file."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cashout error: {error_message}"
        )


@router.post("/cashout/cleanup-stuck")
async def cleanup_stuck_cashouts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clean up stuck cashout transactions that are in PENDING status
    This refunds the Sokocoin balance that was deducted but the transfer failed
    """
    wallet = _get_or_create_wallet(current_user.id, db)
    
    # Find all pending cashout transactions older than 1 hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    stuck_transactions = db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id == wallet.id,
        WalletTransaction.transaction_type == WalletTransactionType.CASHOUT,
        WalletTransaction.status == WalletTransactionStatus.PENDING,
        WalletTransaction.created_at < one_hour_ago
    ).all()
    
    if not stuck_transactions:
        return {
            "success": True,
            "message": "No stuck transactions found",
            "refunded_count": 0
        }
    
    refunded_count = 0
    total_refunded = 0.0
    
    for transaction in stuck_transactions:
        # Refund the Sokocoin balance
        wallet.sokocoin_balance += transaction.sokocoin_amount
        total_refunded += transaction.sokocoin_amount
        transaction.status = WalletTransactionStatus.FAILED
        refunded_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Refunded {refunded_count} stuck transaction(s)",
        "refunded_count": refunded_count,
        "total_sokocoin_refunded": total_refunded
    }


@router.post("/webhook/flutterwave")
async def flutterwave_webhook(
    webhook_data: dict,
    db: Session = Depends(get_db)
):
    """Handle Flutterwave webhook callbacks"""
    try:
        event = webhook_data.get("event")
        data = webhook_data.get("data", {})
        
        if event == "charge.completed":
            tx_ref = data.get("tx_ref")
            status = data.get("status")
            
            if tx_ref and status == "successful":
                # Find transaction by reference
                transaction = db.query(WalletTransaction).filter(
                    WalletTransaction.payment_reference == tx_ref
                ).first()
                
                if transaction and transaction.status == WalletTransactionStatus.PENDING:
                    # Update transaction status
                    transaction.status = WalletTransactionStatus.COMPLETED
                    transaction.completed_at = datetime.now(timezone.utc)
                    transaction.gateway_transaction_id = data.get("id")
                    
                    # Update wallet balance
                    wallet = transaction.wallet
                    wallet.sokocoin_balance += transaction.sokocoin_amount
                    wallet.total_topup += transaction.local_currency_amount or 0
                    
                    # Create notification
                    notification = Notification(
                        user_id=transaction.user_id,
                        notification_type="wallet",
                        title="Top-up Successful",
                        message=f"You have successfully topped up {transaction.sokocoin_amount:.2f} Sokocoin",
                        is_read=False
                    )
                    db.add(notification)
                    db.commit()
        
        return {"status": "success"}
    except Exception as e:
        # Log error but don't fail webhook
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific transaction"""
    wallet = _get_or_create_wallet(current_user.id, db)
    
    transaction = db.query(WalletTransaction).filter(
        WalletTransaction.id == transaction_id,
        WalletTransaction.wallet_id == wallet.id,
        WalletTransaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Allow deletion of all transactions, including completed ones
    # Note: Deleting completed transactions will remove them from history
    # but the wallet balance has already been affected by these transactions
    db.delete(transaction)
    db.commit()
    
    return {
        "success": True,
        "message": "Transaction deleted successfully"
    }


@router.delete("/transactions")
async def delete_all_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all transactions for the current user"""
    wallet = _get_or_create_wallet(current_user.id, db)
    
    # Only delete failed or cancelled transactions
    # Keep completed transactions as they affect wallet balance
    deleted_count = db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id == wallet.id,
        WalletTransaction.user_id == current_user.id,
        WalletTransaction.status.in_([
            WalletTransactionStatus.FAILED,
            WalletTransactionStatus.CANCELLED,
            WalletTransactionStatus.PENDING
        ])
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Deleted {deleted_count} transaction(s)",
        "deleted_count": deleted_count
    }


@router.get("/banks/{country}")
async def get_banks(
    country: str,
    db: Session = Depends(get_db)
):
    """Get list of banks for a country"""
    try:
        banks_response = flutterwave_service.get_banks(country)
        return banks_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching banks: {str(e)}"
        )

