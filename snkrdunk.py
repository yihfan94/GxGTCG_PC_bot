"""
SNKRDUNK provider — free light-personal-use version.
Scrapes public product search / pages for grades A/B/C/D when possible.
"""

import re
import httpx
from bs4 import BeautifulSoup

try:
    from .base import BaseProvider, CardResult
    from utils.currency import format_price, jpy_to_usd
except ImportError:
    from base import BaseProvider, CardResult
    from currency import format_price, jpy_to_usd


class SnkrdunkProvider(BaseProvider):
    name = "SNKRDUNK"

    BASE = "https://snkrdunk.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; TCGPriceBot/1.0)",
        "Accept-Language": "ja,en;q=0.9",
    }

    async def search(self, query: str, limit: int = 8) -> list[CardResult]:
        """Light search — returns empty; prices are fetched after card identification."""
        return []

    async def get_prices(self, card: CardResult) -> CardResult:
        """
        Attempt to find the card on SNKRDUNK and extract grade floors.
        For light personal use this is best-effort; results vary by card name.
        """
        search_term = f"{card.name} {card.set_name}".strip()
        if not search_term:
            return card

        search_url = f"{self.BASE}/search?keyword={search_term}"

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=self.HEADERS) as client:
            try:
                r = await client.get(search_url)
                if r.status_code != 200:
                    return card
                soup = BeautifulSoup(r.text, "lxml")

                # Look for product links
                product_link = None
                for a in soup.select("a[href*='/products/'], a[href*='/trading-cards/']"):
                    href = a.get("href", "")
                    if href:
                        product_link = href if href.startswith("http") else self.BASE + href
                        break

                if not product_link:
                    return card

                # Fetch product page and try to extract grade prices
                pr = await client.get(product_link)
                if pr.status_code != 200:
                    return card
                psoup = BeautifulSoup(pr.text, "lxml")

                # Common patterns for grade prices on SNKRDUNK (A/B/C/D)
                text = psoup.get_text(" ", strip=True)
                for grade, attr in [("A", "snkr_a"), ("B", "snkr_b"), ("C", "snkr_c"), ("D", "snkr_d")]:
                    # Look for patterns like "A ¥12,300" or "Grade A 12300"
                    m = re.search(
                        rf"(?:Grade\s*)?{grade}\s*[¥￥]?\s*([\d,]+)",
                        text,
                        re.IGNORECASE,
                    )
                    if m:
                        try:
                            value = int(m.group(1).replace(",", ""))
                            setattr(card, attr, value)
                        except ValueError:
                            pass

                # Try to improve image
                if not card.image_url:
                    img = psoup.select_one("img[src*='snkrdunk'], img.product-image, meta[property='og:image']")
                    if img:
                        src = img.get("src") or img.get("content")
                        if src:
                            if src.startswith("//"):
                                src = "https:" + src
                            elif src.startswith("/"):
                                src = self.BASE + src
                            card.image_url = src
            except Exception:
                pass

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
