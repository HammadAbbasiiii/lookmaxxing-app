import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # JWT Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change_this_in_production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Admin access — emails allowed on /admin/* (comma-separated).
    # The owner email is always included so the dashboard works out of the box;
    # extra admins can be added via the ADMIN_EMAILS env var (comma-separated).
    ADMIN_EMAILS: list = list(dict.fromkeys(
        ["hammadabbasi732@gmail.com"]
        + [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    ))

    # Environment / payments
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_PRO_MONTHLY: str = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")
    STRIPE_PRICE_PRO_ANNUAL: str = os.getenv("STRIPE_PRICE_PRO_ANNUAL", "")
    STRIPE_PRICE_ELITE_MONTHLY: str = os.getenv("STRIPE_PRICE_ELITE_MONTHLY", "")
    STRIPE_PRICE_ELITE_ANNUAL: str = os.getenv("STRIPE_PRICE_ELITE_ANNUAL", "")
    # Dev/test-only: allows POST /payments/test-upgrade to flip a subscription
    # without a real charge. Ignored when ENVIRONMENT == "production".
    ALLOW_TEST_PAYMENTS: bool = os.getenv("ALLOW_TEST_PAYMENTS", "0") == "1"

    # Freemium limits (server-authoritative §5.2).
    FREE_ANALYSIS_LIMIT: int = int(os.getenv("FREE_ANALYSIS_LIMIT", "1"))

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    CLOUDINARY_UPLOAD_PRESET: str = os.getenv("CLOUDINARY_UPLOAD_PRESET", "")  # e.g., "lookmaxx_upload_preset"
    
    # File upload limits
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".heic"]
    
    # ML Model
    MODEL_PATH: str = os.getenv("MODEL_PATH", "./models/rank_info_net_full.pth")

settings = Settings()

# Security: never allow the insecure default JWT signing key in production.
if settings.SECRET_KEY == "change_this_in_production":
    _env = os.getenv("ENVIRONMENT", "development").lower()
    if _env == "production":
        raise RuntimeError(
            "SECRET_KEY is still the insecure default ('change_this_in_production'). "
            "Set a strong SECRET_KEY environment variable before running in production."
        )
    print("⚠️  SECRET_KEY is using the insecure default — set a real value before deploying.")
