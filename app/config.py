import os
from dataclasses import dataclass

from dotenv import load_dotenv

from app.premium import (
    DEFAULT_PREMIUM_PRICE_RUB,
    DEFAULT_PREMIUM_PRICE_STARS,
    DEFAULT_PREMIUM_PRICE_USD_CENTS,
)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_path: str = "content_saas.db"
    proxy_url: str | None = None
    admin_ids: tuple[int, ...] = ()
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    free_daily_limit: int = 5
    premium_price_stars: int = DEFAULT_PREMIUM_PRICE_STARS
    enable_payments: bool = False
    payment_provider_token: str | None = None
    payment_provider_token_usd: str | None = None
    premium_price_rub: int = DEFAULT_PREMIUM_PRICE_RUB
    premium_price_usd_cents: int = DEFAULT_PREMIUM_PRICE_USD_CENTS


def _parse_int(raw: str, default: int) -> int:
    return int(raw) if raw.isdigit() else default


def load_settings() -> Settings:
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    proxy_url = (
        os.getenv("BOT_PROXY", "").strip()
        or os.getenv("HTTPS_PROXY", "").strip()
        or os.getenv("HTTP_PROXY", "").strip()
        or None
    )

    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = tuple(int(p) for p in admin_ids_raw.split(",") if p.strip().isdigit())

    enable_payments_raw = os.getenv("ENABLE_PAYMENTS", "false").strip().lower()
    enable_payments = enable_payments_raw in {"1", "true", "yes", "on"}

    return Settings(
        bot_token=bot_token,
        proxy_url=proxy_url,
        admin_ids=admin_ids,
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        free_daily_limit=_parse_int(os.getenv("FREE_DAILY_LIMIT", "5").strip(), 5),
        premium_price_stars=_parse_int(
            os.getenv("PREMIUM_PRICE_STARS", str(DEFAULT_PREMIUM_PRICE_STARS)).strip(),
            DEFAULT_PREMIUM_PRICE_STARS,
        ),
        enable_payments=enable_payments,
        payment_provider_token=os.getenv("PAYMENT_PROVIDER_TOKEN", "").strip() or None,
        payment_provider_token_usd=os.getenv("PAYMENT_PROVIDER_TOKEN_USD", "").strip() or None,
        premium_price_rub=_parse_int(
            os.getenv("PREMIUM_PRICE_RUB", str(DEFAULT_PREMIUM_PRICE_RUB)).strip(),
            DEFAULT_PREMIUM_PRICE_RUB,
        ),
        premium_price_usd_cents=_parse_int(
            os.getenv("PREMIUM_PRICE_USD", str(DEFAULT_PREMIUM_PRICE_USD_CENTS)).strip(),
            DEFAULT_PREMIUM_PRICE_USD_CENTS,
        ),
    )
