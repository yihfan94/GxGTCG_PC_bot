"""
Library / collection storage for TCG Price Bot.
JSON-based so backup/restore is a simple file copy.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent / "data"))
DATA_DIR.mkdir(exist_ok=True)
LIBRARY_FILE = DATA_DIR / "library.json"

DEFAULT_DATA = {
    "binders": ["Not in binder", "Sold"],
    "cards": [],          # list of card copies
    "tradeshows": [],     # named date ranges
}


def _load() -> dict:
    if not LIBRARY_FILE.exists():
        return json.loads(json.dumps(DEFAULT_DATA))
    try:
        return json.loads(LIBRARY_FILE.read_text())
    except Exception:
        return json.loads(json.dumps(DEFAULT_DATA))


def _save(data: dict) -> None:
    LIBRARY_FILE.write_text(json.dumps(data, indent=2, default=str))


def get_binders() -> list[str]:
    return _load()["binders"]


def add_binder(name: str) -> bool:
    data = _load()
    if name in data["binders"] or name in ("Not in binder", "Sold"):
        return False
    data["binders"].append(name)
    _save(data)
    return True


def move_card(card_id: str, new_binder: str) -> bool:
    data = _load()
    if new_binder not in data["binders"]:
        return False
    for c in data["cards"]:
        if c["id"] == card_id:
            c["binder"] = new_binder
            _save(data)
            return True
    return False


def add_card(
    name: str,
    bought_price: float,
    quantity: int = 1,
    notes: str = "",
    image_url: str = "",
    set_name: str = "",
) -> str:
    data = _load()
    card_id = f"card_{int(datetime.utcnow().timestamp() * 1000)}"
    data["cards"].append({
        "id": card_id,
        "name": name,
        "set_name": set_name,
        "bought_price": bought_price,
        "quantity": quantity,
        "notes": notes,
        "image_url": image_url,
        "binder": "Not in binder",
        "sold_price": None,
        "sold_date": None,
        "added_date": datetime.utcnow().isoformat(),
    })
    _save(data)
    return card_id


def mark_sold(card_id: str, sold_price: float) -> bool:
    data = _load()
    for c in data["cards"]:
        if c["id"] == card_id:
            c["sold_price"] = sold_price
            c["sold_date"] = datetime.utcnow().isoformat()
            c["binder"] = "Sold"
            _save(data)
            return True
    return False


def get_cards(binder: Optional[str] = None) -> list[dict]:
    cards = _load()["cards"]
    if binder:
        return [c for c in cards if c["binder"] == binder]
    return cards


def add_tradeshow(name: str, start: str, end: str) -> bool:
    data = _load()
    if any(t["name"].lower() == name.lower() for t in data["tradeshows"]):
        return False
    data["tradeshows"].append({"name": name, "start": start, "end": end})
    _save(data)
    return True


def get_tradeshow(name: str) -> Optional[dict]:
    for t in _load()["tradeshows"]:
        if t["name"].lower() == name.lower():
            return t
    return None


def export_library() -> str:
    """Return path to the current library file for backup."""
    return str(LIBRARY_FILE)


def import_library(content: str) -> bool:
    try:
        data = json.loads(content)
        if "cards" not in data or "binders" not in data:
            return False
        LIBRARY_FILE.write_text(json.dumps(data, indent=2))
        return True
    except Exception:
        return False
