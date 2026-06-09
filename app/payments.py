from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.config import Settings
from app.premium import (
    DEFAULT_PREMIUM_PRICE_RUB,
    DEFAULT_PREMIUM_PRICE_STARS,
    DEFAULT_PREMIUM_PRICE_USD_CENTS,
)


class PayCurrency(StrEnum):
    STARS = "stars"
    RUB = "rub"
    USD = "usd"


@dataclass(frozen=True)
class PremiumPaymentOption:
    currency: PayCurrency
    invoice_amount: int
    telegram_currency: str
    provider_token: str
    button_label: str
    panel_label: str


def premium_payload(currency: PayCurrency) -> str:
    return f"premium_30d:{currency.value}"


def parse_premium_payload(payload: str) -> PayCurrency | None:
    if payload == "premium_30d":
        return PayCurrency.STARS
    if not payload.startswith("premium_30d:"):
        return None
    suffix = payload.split(":", 1)[1]
    try:
        return PayCurrency(suffix)
    except ValueError:
        return None


def _format_usd(cents: int) -> str:
    return f"${cents / 100:.2f}"


def available_payment_options(settings: Settings) -> tuple[PremiumPaymentOption, ...]:
    if not settings.enable_payments:
        return ()

    options: list[PremiumPaymentOption] = []

    if settings.premium_price_stars > 0:
        options.append(
            PremiumPaymentOption(
                currency=PayCurrency.STARS,
                invoice_amount=settings.premium_price_stars,
                telegram_currency="XTR",
                provider_token="",
                button_label=f"⭐ {settings.premium_price_stars} Stars",
                panel_label=f"⭐ {settings.premium_price_stars} Stars",
            )
        )

    if settings.payment_provider_token and settings.premium_price_rub > 0:
        options.append(
            PremiumPaymentOption(
                currency=PayCurrency.RUB,
                invoice_amount=settings.premium_price_rub * 100,
                telegram_currency="RUB",
                provider_token=settings.payment_provider_token,
                button_label=f"💳 {settings.premium_price_rub} ₽",
                panel_label=f"💳 {settings.premium_price_rub} ₽",
            )
        )

    usd_token = settings.payment_provider_token_usd or settings.payment_provider_token
    if usd_token and settings.premium_price_usd_cents > 0:
        usd_label = _format_usd(settings.premium_price_usd_cents)
        options.append(
            PremiumPaymentOption(
                currency=PayCurrency.USD,
                invoice_amount=settings.premium_price_usd_cents,
                telegram_currency="USD",
                provider_token=usd_token,
                button_label=f"💵 {usd_label}",
                panel_label=f"💵 {usd_label}",
            )
        )

    return tuple(options)


def get_payment_option(settings: Settings, currency: PayCurrency) -> PremiumPaymentOption | None:
    for option in available_payment_options(settings):
        if option.currency == currency:
            return option
    return None
