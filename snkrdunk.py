"""
SNKRDUNK provider (placeholder).

Best long-term option: ReefAPI SNKRDUNK endpoints
(search + prices_by_condition for grades A/B/C/D).
"""

try:
    from .base import BaseProvider, CardResult
    from utils.currency import format_price, jpy_to_usd
except ImportError:
    from base import BaseProvider, CardResult
    from currency import format_price, jpy_to_usd


class SnkrdunkProvider(BaseProvider):
    name = "SNKRDUNK"

    async def search(self, query: str, limit: int = 8) -> list[CardResult]:
        # SNKRDUNK is also better used after card identification
        return []

    async def get_prices(self, card: CardResult) -> CardResult:
        # TODO: Real SNKRDUNK floor prices by grade A/B/C/D (in JPY)
        if "charizard" in card.name.lower():
            card.snkr_a = 18500
            card.snkr_b = 14200
            card.snkr_c = 9800
            card.snkr_d = 6500
        elif "luffy" in card.name.lower():
            card.snkr_a = 2800
            card.snkr_b = 2100
            card.snkr_c = 1500
            card.snkr_d = 900
        else:
            card.snkr_a = 3500
            card.snkr_b = 2800
            card.snkr_c = 1900
            card.snkr_d = 1200
        return card

    def format_prices(self, card: CardResult) -> str:
        lines = ["*SNKRDUNK (JP Raw)*"]
        for grade, value in [
            ("A", card.snkr_a),
            ("B", card.snkr_b),
            ("C", card.snkr_c),
            ("D", card.snkr_d),
        ]:
            usd = jpy_to_usd(value)
            lines.append(
                f"• Grade {grade}: {format_price(value, 'JPY')} "
                f"(~{format_price(usd)})"
            )
        return "\n".join(lines)