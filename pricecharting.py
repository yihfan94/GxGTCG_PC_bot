"""
PriceCharting provider — free light-personal-use version.
Uses public search + product pages. No paid API required.
"""

import re
import httpx
from bs4 import BeautifulSoup

try:
    from .base import BaseProvider, CardResult
    from utils.currency import format_price
except ImportError:
    from base import BaseProvider, CardResult
    from currency import format_price


class PriceChartingProvider(BaseProvider):
    name = "PriceCharting"

    BASE = "https://www.pricecharting.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; TCGPriceBot/1.0; +https://github.com)",
        "Accept": "text/html,application/xhtml+xml",
    }

    async def _search_pokemontcg(self, query: str, limit: int = 8) -> list[CardResult]:
        """Free search of all printed Pokémon cards via TCGdex (no key needed)."""
        results = []
        clean = " ".join(query.split())
        # TCGdex search endpoint
        url = "https://api.tcgdex.net/v2/en/cards"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # Simple name filter works
                r = await client.get(url, params={"name": clean})
                if r.status_code != 200 or not r.json():
                    first = clean.split()[0]
                    r = await client.get(url, params={"name": first})
                if r.status_code != 200:
                    return results
                data = r.json()
                # TCGdex returns a list of cards
                cards = data if isinstance(data, list) else data.get("data", [])
                # Prefer cards that match a number in the query
                import re
                num_match = re.search(r'\b(\d{1,4})\b', clean)
                if num_match:
                    want = num_match.group(1).lstrip("0") or "0"
                    def score(c):
                        num = str(c.get("localId") or c.get("number") or "")
                        n = num.lstrip("0") or "0"
                        return 0 if n == want else 1
                    cards.sort(key=score)
                cards = [c for c in cards if c.get('image')][:limit] or cards[:limit]
                for card in cards[:limit]:
                    img = None
                    images = card.get("image") or card.get("images") or {}
                    if isinstance(images, dict):
                        img = images.get("large") or images.get("small") or images.get("high")
                    elif isinstance(images, str):
                        img = images
                    results.append(CardResult(
                        id=card.get("id", ""),
                        name=card.get("name", clean),
                        set_name=card.get("set", {}).get("name", "") if isinstance(card.get("set"), dict) else "",
                        number=str(card.get("localId") or card.get("number") or ""),
                        game="pokemon",
                        language="EN",
                        image_url=img,
                    ))
        except Exception:
            pass
        return results

    async def search(self, query: str, limit: int = 8) -> list[CardResult]:
        """Search all Pokémon cards (Pokémon TCG API first, then PriceCharting)."""
        # Prefer the free API that covers all printed cards
        results = await self._search_pokemontcg(query, limit)
        if results:
            return results

        # Fallback to PriceCharting scrape
        results: list[CardResult] = []
        search_url = f"{self.BASE}/search-products?q={query}&type=prices"

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=self.HEADERS) as client:
            try:
                r = await client.get(search_url)
                if r.status_code != 200:
                    return results
                soup = BeautifulSoup(r.text, "lxml")

                # Product links on search results
                for a in soup.select("a[href*='/game/']")[:limit * 2]:
                    href = a.get("href", "")
                    if not href or "/game/" not in href:
                        continue
                    full_url = href if href.startswith("http") else self.BASE + href
                    name = a.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    # Try to get image from the link or nearby
                    img = a.find("img")
                    image_url = None
                    if img and img.get("src"):
                        image_url = img["src"]
                        if image_url.startswith("//"):
                            image_url = "https:" + image_url
                        elif image_url.startswith("/"):
                            image_url = self.BASE + image_url

                    card = CardResult(
                        id=full_url,
                        name=name,
                        set_name="",  # filled on detail fetch if needed
                        game="pokemon" if "pokemon" in query.lower() or "pokémon" in query.lower() else "",
                        language="EN",
                        image_url=image_url,
                    )
                    # Avoid duplicates
                    if not any(c.id == card.id for c in results):
                        results.append(card)
                    if len(results) >= limit:
                        break
            except Exception:
                pass

        # Fallback for Pokémon cards if PriceCharting returned nothing
        if not results:
            results = await self._search_pokemontcg(query, limit)

        return results

    async def get_prices(self, card: CardResult) -> CardResult:
        """Fetch ungraded EN price from the product page."""
        if not card.id or not card.id.startswith("http"):
            return card

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=self.HEADERS) as client:
            try:
                r = await client.get(card.id)
                if r.status_code != 200:
                    return card
                soup = BeautifulSoup(r.text, "lxml")

                # Look for ungraded price (common patterns)
                price_text = None
                for selector in [
                    "td.price",
                    ".price",
                    "[data-price]",
                    "span.price",
                ]:
                    el = soup.select_one(selector)
                    if el:
                        price_text = el.get_text(strip=True)
                        break

                if price_text:
                    # Extract number
                    m = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                    if m:
                        try:
                            card.pc_ungraded_en = float(m.group())
                        except ValueError:
                            pass

                # Try to improve image if missing
                if not card.image_url:
                    img = soup.select_one("img[src*='pricecharting'], img.product-image, #product-image img")
                    if img and img.get("src"):
                        src = img["src"]
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = self.BASE + src
                        card.image_url = src
            except Exception:
                pass

        return card

    def format_prices(self, card: CardResult) -> str:
        lines = ["*PriceCharting (Ungraded)*"]
        lines.append(f"• EN: {format_price(card.pc_ungraded_en)}")
        lines.append(f"• JP: {format_price(card.pc_ungraded_jp)}")
        return "\n".join(lines)
