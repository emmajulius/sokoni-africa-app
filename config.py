try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pathlib import Path
    
    # Pydantic v2
    HAS_V2 = True
except ImportError:
    # Fallback for older pydantic versions
    try:
        from pydantic import BaseSettings
        from pathlib import Path
        HAS_V2 = False
        SettingsConfigDict = None
    except ImportError:
        raise ImportError("pydantic or pydantic-settings is required")

from typing import List, Optional

# Get the directory where this config file is located
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

if HAS_V2:
    # Pydantic v2 configuration
    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=str(ENV_FILE),
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore"  # Ignore extra fields in .env file
        )
        
        # Database
        DATABASE_URL: str
        
        # JWT
        SECRET_KEY: str
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
        
        # App
        DEBUG: bool = True
        ENVIRONMENT: str = "development"
        APP_BASE_URL: str = "http://localhost:8000"
        
        # CORS
        ALLOWED_ORIGINS: str = "*"  # Allow all origins for mobile apps (restrict in production)
        ALLOWED_ORIGIN_REGEX: str = r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+)(:\d+)?"
        
        # Flutterwave
        FLW_SECRET_KEY: str = ""
        FLW_PUBLIC_KEY: str = ""
        FLW_ENCRYPTION_KEY: str = ""
        FLUTTERWAVE_BASE_URL: str = "https://api.flutterwave.com/v3"  # v4 credentials but v3 endpoints
        MOCK_CASHOUT_TRANSFERS: bool = False
        MOCK_FLUTTERWAVE_TOPUPS: bool = False
        
        # Email
        EMAIL_HOST: str = "smtp.gmail.com"
        EMAIL_PORT: int = 587
        EMAIL_USE_TLS: bool = True
        EMAIL_USERNAME: str = "emmajulius2512@gmail.com"
        EMAIL_PASSWORD: str = "wyehxgjynsrvkphl"
        EMAIL_FROM: str = "emmajulius2512@gmail.com"
        EMAIL_FROM_NAME: str = "Research Gears"
        
        # Sokocoin Exchange Rate (1 Sokocoin = X local currency)
        # This can be configured per currency
        # Base conversion:
        # 1 SOK = 1000 TZS (reference)
        # 1 TZS = 0.0527 KES  => 1 SOK = 52.7 KES
        # 1 TZS = 0.587  NGN  => 1 SOK = 587 NGN
        SOKOCOIN_EXCHANGE_RATE_TZS: float = 1000.0  # 1 Sokocoin = 1000 TZS
        SOKOCOIN_EXCHANGE_RATE_KES: float = 52.7    # 1 Sokocoin = 52.7 KES
        SOKOCOIN_EXCHANGE_RATE_NGN: float = 587.0   # 1 Sokocoin = 587 NGN
        
        # Platform fees
        PROCESSING_FEE_RATE: float = 0.02  # 2% processing fee
        
        # Shipping configuration (all values expressed in Sokocoin and kilometers)
        SHIPPING_BASE_FEE_SOK: float = 2.0  # Minimum fee applied when logistics is selected
        SHIPPING_RATE_PER_KM_SOK: float = 0.5  # Additional SOK charged per kilometer
        SHIPPING_MIN_DISTANCE_KM: float = 1.0  # Distances below this threshold are treated as this value
        
        # Backward compatibility - map old names to new names
        @property
        def FLUTTERWAVE_SECRET_KEY(self) -> str:
            return self.FLW_SECRET_KEY
        
        @property
        def FLUTTERWAVE_PUBLIC_KEY(self) -> str:
            return self.FLW_PUBLIC_KEY
        
        @property
        def FLUTTERWAVE_ENCRYPTION_KEY(self) -> str:
            return self.FLW_ENCRYPTION_KEY
        
        @property
        def cors_origins(self) -> List[str]:
            """
            Returns an explicit list of allowed origins. When ALLOWED_ORIGINS is '*',
            we keep the literal wildcard so that all origins are accepted.
            """
            if self.ALLOWED_ORIGINS == "*":
                return ["*"]
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

        @property
        def cors_origin_regex(self) -> Optional[str]:
            """
            Provides a permissive regex for common localhost / LAN development origins.
            When ALLOWED_ORIGINS is '*', we can skip the regex entirely so that Starlette
            will respond with the wildcard in Access-Control-Allow-Origin (still compatible
            with credentials because we manage headers explicitly).
            """
            if self.ALLOWED_ORIGINS == "*":
                return None
            return self.ALLOWED_ORIGIN_REGEX or None
else:
    # Pydantic v1 configuration
    class Settings(BaseSettings):
        # Database
        DATABASE_URL: str
        
        # JWT
        SECRET_KEY: str
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
        
        # App
        DEBUG: bool = True
        ENVIRONMENT: str = "development"
        APP_BASE_URL: str = "http://localhost:8000"
        
        # CORS
        ALLOWED_ORIGINS: str = "*"  # Allow all origins for mobile apps (restrict in production)
        ALLOWED_ORIGIN_REGEX: str = r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+)(:\d+)?"
        
        # Flutterwave
        FLW_SECRET_KEY: str = ""
        FLW_PUBLIC_KEY: str = ""
        FLW_ENCRYPTION_KEY: str = ""
        FLUTTERWAVE_BASE_URL: str = "https://api.flutterwave.com/v3"  # v4 credentials but v3 endpoints
        MOCK_CASHOUT_TRANSFERS: bool = False
        MOCK_FLUTTERWAVE_TOPUPS: bool = False
        
        # Email
        EMAIL_HOST: str = "smtp.gmail.com"
        EMAIL_PORT: int = 587
        EMAIL_USE_TLS: bool = True
        EMAIL_USERNAME: str = "emmajulius2512@gmail.com"
        EMAIL_PASSWORD: str = "wyehxgjynsrvkphl"
        EMAIL_FROM: str = "emmajulius2512@gmail.com"
        EMAIL_FROM_NAME: str = "Research Gears"
        
        # Sokocoin Exchange Rate (1 Sokocoin = X local currency)
        # This can be configured per currency
        # Base conversion:
        # 1 SOK = 1000 TZS (reference)
        # 1 TZS = 0.0527 KES  => 1 SOK = 52.7 KES
        # 1 TZS = 0.587  NGN  => 1 SOK = 587 NGN
        SOKOCOIN_EXCHANGE_RATE_TZS: float = 1000.0  # 1 Sokocoin = 1000 TZS
        SOKOCOIN_EXCHANGE_RATE_KES: float = 52.7    # 1 Sokocoin = 52.7 KES
        SOKOCOIN_EXCHANGE_RATE_NGN: float = 587.0   # 1 Sokocoin = 587 NGN
        
        # Platform fees
        PROCESSING_FEE_RATE: float = 0.02  # 2% processing fee
        
        # Shipping configuration (all values expressed in Sokocoin and kilometers)
        SHIPPING_BASE_FEE_SOK: float = 2.0  # Minimum fee applied when logistics is selected
        SHIPPING_RATE_PER_KM_SOK: float = 0.5  # Additional SOK charged per kilometer
        SHIPPING_MIN_DISTANCE_KM: float = 1.0  # Distances below this threshold are treated as this value
        
        # Backward compatibility - map old names to new names
        @property
        def FLUTTERWAVE_SECRET_KEY(self) -> str:
            return self.FLW_SECRET_KEY
        
        @property
        def FLUTTERWAVE_PUBLIC_KEY(self) -> str:
            return self.FLW_PUBLIC_KEY
        
        @property
        def FLUTTERWAVE_ENCRYPTION_KEY(self) -> str:
            return self.FLW_ENCRYPTION_KEY
        
        @property
        def cors_origins(self) -> List[str]:
            """
            Returns an explicit list of allowed origins. When ALLOWED_ORIGINS is '*',
            we keep the literal wildcard so that all origins are accepted.
            """
            if self.ALLOWED_ORIGINS == "*":
                return ["*"]
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

        @property
        def cors_origin_regex(self) -> Optional[str]:
            """
            Provides a permissive regex for common localhost / LAN development origins.
            When ALLOWED_ORIGINS is '*', we can skip the regex entirely so that Starlette
            will respond with the wildcard in Access-Control-Allow-Origin (still compatible
            with credentials because we manage headers explicitly).
            """
            if self.ALLOWED_ORIGINS == "*":
                return None
            return self.ALLOWED_ORIGIN_REGEX or None
        
        class Config:
            env_file = str(ENV_FILE)
            env_file_encoding = "utf-8"
            case_sensitive = True
            extra = "ignore"  # Ignore extra fields in .env file


# Initialize settings
settings = Settings()

