from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CardResult:
    """Unified card object returned by all providers."""
    id: str
    name: str
    set_name: str
    number: str = ""
    game: str = ""                  # "pokemon" or "onepiece"
    language: str = "EN"            # EN / JP / etc.
    image_url: Optional[str] = None
    # PriceCharting style
    pc_ungraded_en: Optional[float] = None
    pc_ungraded_jp: Optional[float] = None
    # eBay
    ebay_mint: Optional[float] = None
    ebay_nm: Optional[float] = None
    ebay_lp: Optional[float] = None
    ebay_mp: Optional[float] = None
    ebay_hp: Optional[float] = None
    ebay_dmg: Optional[float] = None
    ebay_avg_last10: Optional[float] = None
    # SNKRDUNK
    snkr_a: Optional[float] = None  # JPY
    snkr_b: Optional[float] = None
    snkr_c: Optional[float] = None
    snkr_d: Optional[float] = None
    extra: dict = field(default_factory=dict)


class BaseProvider:
    """Interface that every price source should implement."""

    name: str = "base"

    async def search(self, query: str, limit: int = 8) -> list[CardResult]:
        """Return a list of matching cards (with images if possible)."""
        raise NotImplementedError

    async def get_prices(self, card: CardResult) -> CardResult:
        """Enrich a card with price data from this source."""
        raise NotImplementedError