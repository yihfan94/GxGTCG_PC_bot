"""
PriceCharting provider (placeholder).

Later you can replace the mock data with:
- Official PriceCharting API (paid)
- Apify actors
- Careful scraping (needs Cloudflare bypass)
"""

try:
    from .base import BaseProvider, CardResult
    from utils.currency import format_price
except ImportError:
    from base import BaseProvider, CardResult
    from currency import format_price


class PriceChartingProvider(BaseProvider):
    name = "PriceCharting"

    async def search(self, query: str, limit: int = 8) -> list[CardResult]:
        # TODO: Real search against PriceCharting
        # For now return a couple of realistic mock results so the bot works end-to-end
        q = query.lower()
        results = []

        if "charizard" in q or "151" in q:
            results.append(CardResult(
                id="pc-charizard-sv2a-201",
                name="Charizard ex SAR",
                set_name="Pokémon Card 151 (SV2a)",
                number="201/165",
                game="pokemon",
                language="JP",
                image_url="https://images.pokemontcg.io/sv2a/201_hires.png",
                pc_ungraded_en=85.00,
                pc_ungraded_jp=120.00,
            ))
            results.append(CardResult(
                id="pc-charizard-base-4",
                name="Charizard",
                set_name="Base Set",
                number="4/102",
                game="pokemon",
                language="EN",
                image_url="https://images.pokemontcg.io/base1/4_hires.png",
                pc_ungraded_en=320.00,
                pc_ungraded_jp=None,
            ))

        if "luffy" in q or "op01" in q:
            results.append(CardResult(
                id="pc-luffy-op01-003",
                name="Monkey D. Luffy",
                set_name="Romance Dawn (OP01)",
                number="OP01-003",
                game="onepiece",
                language="EN",
                image_url="https://limitlesstcg.s3.us-east-2.amazonaws.com/one-piece/OP01/OP01-003_en_M.png",
                pc_ungraded_en=12.50,
                pc_ungraded_jp=18.00,
            ))

        if not results:
            # Generic fallback so the bot never returns empty during development
            results.append(CardResult(
                id="pc-demo-1",
                name=f"[Demo] {query.title()}",
                set_name="Demo Set",
                number="001",
                game="pokemon",
                language="EN",
                image_url="https://images.pokemontcg.io/base1/4_hires.png",
                pc_ungraded_en=25.00,
                pc_ungraded_jp=30.00,
            ))

        return results[:limit]

    async def get_prices(self, card: CardResult) -> CardResult:
        # In real implementation you would fetch latest prices here
        return card

    def format_prices(self, card: CardResult) -> str:
        lines = ["*PriceCharting (Ungraded)*"]
        lines.append(f"• EN: {format_price(card.pc_ungraded_en)}")
        lines.append(f"• JP: {format_price(card.pc_ungraded_jp)}")
        return "\n".join(lines)