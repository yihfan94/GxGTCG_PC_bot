"""
eBay last-sold provider — free light-personal-use version.

For reliable free use, sign up for a free tier (CompSniper / SoldComps ~100 requests/month)
and set EBAY_SOLD_API_KEY in the environment. This version falls back to a simple note
when no key is present.
"""

import os
import httpx

try:
    from .base import BaseProvider, CardResult
    from utils.currency import format_price
except ImportError:
    from base import BaseProvider, CardResult
    from currency import format_price


class EbayProvider(BaseProvider):
    name = "eBay"

    async def search(self, query: str, limit: int = 8) -> list[CardResult]:
        return []

    async def get_prices(self, card: CardResult) -> CardResult:
        """
        Free-tier path:
        - If EBAY_SOLD_API_KEY is set, call a free sold API (example structure).
        - Otherwise leave prices empty and note that a free key improves accuracy.
        """
        api_key = os.getenv("EBAY_SOLD_API_KEY", "")
        if not api_key:
            # No free key configured — leave as N/A
            return card

        # Example call structure for a free sold API (adjust endpoint to your chosen provider)
        # CompSniper / SoldComps style
        search_term = f"{card.name} {card.set_name}".strip()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Placeholder endpoint — replace with the free API you sign up for
                # e.g. CompSniper, SoldComps, etc.
                r = await client.get(
                    "https://api.example-sold-api.com/sold",  # replace
                    params={"q": search_term, "limit": 10},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    # Parse average of last 10 if the API returns a list
                    sales = data.get("results", data.get("sales", []))
                    prices = []
                    for s in sales[:10]:
                        p = s.get("soldPrice") or s.get("price") or s.get("sold_price")
                        if isinstance(p, (int, float)):
                            prices.append(float(p))
                        elif isinstance(p, str):
                            try:
                                prices.append(float(p.replace("$", "").replace(",", "")))
                            except ValueError:
                                pass
                    if prices:
                        card.ebay_avg_last10 = round(sum(prices) / len(prices), 2)
                        # Rough condition buckets if the API provides condition
                        # (real parsing depends on the API response shape)
        except Exception:
            pass

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
        if not any([card.ebay_mint, card.ebay_nm, card.ebay_avg_last10]):
            lines.append("_Tip: set EBAY_SOLD_API_KEY for free-tier data_")
        return "\n".join(lines)
