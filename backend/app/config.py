import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    # Database (empty env var → local SQLite so the app can always boot).
    DATABASE_URL: str = os.getenv("DATABASE_URL") or "sqlite:///./lookmaxx.db"
    
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

    # CORS allow-list (§19). The API authenticates via bearer tokens in the
    # Authorization header (not cookies), so `allow_credentials` stays False and
    # the browser can send any of these origins without a wildcard+credentials
    # conflict. Native iOS clients don't enforce CORS, so they are unaffected.
    # Explicit CORS_ORIGINS always wins. In production we never fall back to
    # localhost origins (only FRONTEND_URL); in development the local origins are
    # included so the web client works out of the box.
    CORS_ORIGINS: list = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
    ] or (
        [FRONTEND_URL]
        if ENVIRONMENT == "production"
        else [
            FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ]
    )
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_PRO_MONTHLY: str = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")
    STRIPE_PRICE_PRO_ANNUAL: str = os.getenv("STRIPE_PRICE_PRO_ANNUAL", "")
    STRIPE_PRICE_ELITE_MONTHLY: str = os.getenv("STRIPE_PRICE_ELITE_MONTHLY", "")
    STRIPE_PRICE_ELITE_ANNUAL: str = os.getenv("STRIPE_PRICE_ELITE_ANNUAL", "")
    # Dev/test-only: allows POST /payments/test-upgrade to flip a subscription
    # without a real charge. Ignored when ENVIRONMENT == "production".
    ALLOW_TEST_PAYMENTS: bool = os.getenv("ALLOW_TEST_PAYMENTS", "0") == "1"

    # Email / password reset
    # EMAIL_PROVIDER: "console" (logs the reset link — dev/test default) or "smtp".
    # In production set EMAIL_PROVIDER=smtp + SMTP_* so reset links are actually
    # delivered; otherwise the link is logged and no email is sent (never crashes).
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "console")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@lookmaxx.app")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "LookMaxx")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "1") == "1"
    PASSWORD_RESET_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "30"))

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

# Security: never allow a weak/default JWT signing key in production.
if settings.ENVIRONMENT == "production":
    if settings.SECRET_KEY == "change_this_in_production":
        raise RuntimeError(
            "SECRET_KEY is still the insecure default ('change_this_in_production'). "
            "Set a strong SECRET_KEY environment variable before running in production."
        )
    if len(settings.SECRET_KEY) < 32:
        raise RuntimeError(
            f"SECRET_KEY must be at least 32 characters in production "
            f"(got {len(settings.SECRET_KEY)}). Generate one with: "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
elif settings.SECRET_KEY == "change_this_in_production" or len(settings.SECRET_KEY) < 32:
    print("⚠️  SECRET_KEY is weak (default or <32 chars) — set a strong value before deploying.")
