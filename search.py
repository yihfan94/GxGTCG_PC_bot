"""Helpers for normalizing card search queries."""

import re


def normalize_query(text: str) -> str:
    """Clean user input a bit."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def detect_game(query: str) -> str | None:
    """Very light heuristic. Returns 'pokemon', 'onepiece', or None."""
    q = query.lower()
    if any(w in q for w in ("pokemon", "pokémon", "pkmn", "charizard", "pikachu", "mew")):
        return "pokemon"
    if any(w in q for w in ("one piece", "onepiece", "op0", "op1", "luffy", "zoro", "nami")):
        return "onepiece"
    return None