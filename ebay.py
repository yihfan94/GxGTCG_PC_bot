"""
eBay last-sold provider (placeholder).

Real implementation options:
- Third-party sold APIs (Trawl, CompSniper, SoldComps, etc.)
- Construct sold search URLs + careful scraping (fragile)
"""

try:
    from .base import BaseProvider, CardResult
    from utils.currency import format_price
except ImportError:
    from base import BaseProvider, CardResult
    from currency import format_price


class EbayProvider(BaseProvider):
    name = "eBay"

    async def search(self, query: str, limit: int = 8) -> list[CardResult]:
        # eBay is usually used after a card is identified, not as primary search
        return []

    async def get_prices(self, card: CardResult) -> CardResult:
        # TODO: Replace with real last-sold data by condition
        # Mock realistic numbers for development
        if "charizard" in card.name.lower():
            card.ebay_mint = 95.00
            card.ebay_nm = 82.00
            card.ebay_lp = 65.00
            card.ebay_mp = 48.00
            card.ebay_hp = 32.00
            card.ebay_dmg = 18.00
            card.ebay_avg_last10 = 78.50
        elif "luffy" in card.name.lower():
            card.ebay_mint = 14.00
            card.ebay_nm = 11.50
            card.ebay_lp = 8.00
            card.ebay_mp = 5.50
            card.ebay_hp = 3.50
            card.ebay_dmg = 2.00
            card.ebay_avg_last10 = 10.80
        else:
            card.ebay_nm = 20.00
            card.ebay_avg_last10 = 18.50
        return card

    def format_prices(self, card: CardResult) -> str:
        lines = ["*eBay Last Sold (Raw)*"]
        lines.append(f"• Mint: {format_price(card.ebay_mint)}")
        lines.append(f"• Near Mint: {format_price(card.ebay_nm)}")
        lines.append(f"• Lightly Played: {format_price(card.ebay_lp)}")
        lines.append(f"• Moderately Played: {format_price(card.ebay_mp)}")
        lines.append(f"• Heavily Played: {format_price(card.ebay_hp)}")
        lines.append(f"• Damaged: {format_price(card.ebay_dmg)}")
        lines.append(f"• Avg last 10 sales: {format_price(card.ebay_avg_last10)}")
        return "\n".join(lines)