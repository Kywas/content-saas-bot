from __future__ import annotations

from datetime import datetime, timedelta, timezone

PREMIUM_PERIOD_DAYS = 30
PREMIUM_PAYLOAD = "premium_30d"

DEFAULT_PREMIUM_PRICE_STARS = 149
DEFAULT_PREMIUM_PRICE_RUB = 299
DEFAULT_PREMIUM_PRICE_USD_CENTS = 499


def is_premium_active(premium_until: str | None) -> bool:
    if not premium_until:
        return False
    try:
        until = datetime.fromisoformat(premium_until)
    except ValueError:
        return False
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > datetime.now(timezone.utc)


def extend_premium_until(
    premium_until: str | None,
    days: int = PREMIUM_PERIOD_DAYS,
) -> datetime:
    now = datetime.now(timezone.utc)
    base = now
    if premium_until:
        try:
            parsed = datetime.fromisoformat(premium_until)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed > now:
                base = parsed
        except ValueError:
            pass
    return base + timedelta(days=max(1, days))


def format_premium_until(until_iso: str | None) -> str:
    if not until_iso:
        return "—"
    try:
        until = datetime.fromisoformat(until_iso)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
    except ValueError:
        return until_iso
    return until.strftime("%d.%m.%Y")
