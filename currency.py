"""Simple currency helpers. You can later plug in a live FX rate API."""

# Rough static rate (update periodically or replace with live API)
JPY_TO_USD = 0.0067  # ~150 JPY = 1 USD as of late 2026


def jpy_to_usd(jpy: float | int | None) -> float | None:
    if jpy is None:
        return None
    return round(float(jpy) * JPY_TO_USD, 2)


def format_price(amount: float | int | None, currency: str = "USD") -> str:
    if amount is None:
        return "N/A"
    if currency.upper() == "JPY":
        return f"¥{int(amount):,}"
    return f"${float(amount):,.2f}"