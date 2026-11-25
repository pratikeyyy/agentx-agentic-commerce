"""Tests for the official Techfest dev-set adapter (app/official_agent.py).

The adapter parses the streaming word-by-word requests into the 5 gold
filters (category, colour, size, brand, max_price) and commits only when
the filters are stable and singleton. These tests pin the parser behaviours
that the official 300-request dev set exercises: synonyms, number words,
Hindi code-mixing, corrections (last mention wins), and the commit guards.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.official_agent import Agent, parse_filters  # noqa: E402


def _parse(text):
    return parse_filters(text.split())


def test_synonyms_and_sizes():
    f = _parse("black rucksack up to 1,500, from Urbanyx")
    assert f["category"] == "backpacks"
    assert f["colour"] == "black"
    assert f["brand"] == "Urbanyx"
    assert f["max_price"] == 1500
    f = _parse("size eight actually six slides from Urbanyx budget 800")
    assert f["size"] == "6"  # bare number word before a category phrase


def test_number_words_and_decimal_k():
    f = _parse("under seventy five hundred, in gray, Pacevo brand, size 9 UK")
    assert f["max_price"] == 7500
    f = _parse("black running sneakers up to four thousand five hundred. one more thing, size 8 UK")
    assert f["max_price"] == 4500  # the "one" of "one more thing" is not part of the price
    f = _parse("white sneakers up to rs 7500, size 10")
    assert f["max_price"] == 7500
    f = _parse("budget 0.7k by Tikkra, in golden")
    assert f["max_price"] == 700


def test_hindi_code_mixed():
    f = _parse("mujhe Pacevo navy casual sneakers das number hai kya?")
    assert f["size"] == "10"  # "das number" = size 10
    f = _parse("bhaiya, dikhao olive Urbanyx jacket size S dhai hazaar tak chahiye please")
    assert f["max_price"] == 2500  # "dhai hazaar" = 2500
    f = _parse("kya aapke paas black trackpants Zentrail ka M size nahi, small, 1700 se kam hai kya?")
    assert f["max_price"] == 1700  # "1700 se kam" = less than 1700
    f = _parse("mujhe grey Zentrail joggers satrah sau ke andar size M chahiye please")
    assert f["max_price"] == 1700


def test_corrections_last_mention_wins():
    f = _parse("get me olive size eight actually six slides from Urbanyx budget 800")
    assert f["size"] == "6"
    f = _parse("black rucksack up to 1,500, from Zentrail, sorry, from Urbanyx")
    assert f["brand"] == "Urbanyx"
    f = _parse("hey, do you have any wrist watch budget 4.5k by Tikkra, in golden no no, in blue for a wedding")
    assert f["colour"] == "blue"


def test_standalone_letter_sizes_are_not_words_inside_words():
    # "I'm" contains an "m" and "it's" an "s" — neither is a size.
    f = _parse("I'm looking for a black jacket, it's nice, size L")
    assert f["size"] == "L"
    f = _parse("I'm looking for grey floaters UK 7 no no, UK 6, not more than seven hundred")
    assert f["size"] == "6"


class _FakeTools:
    """Minimal tools.search: exact-filter match over a tiny catalogue."""

    def __init__(self, products):
        self.products = products

    def search(self, query, filters, k=5):
        def _ok(p):
            for key, value in filters.items():
                if key == "max_price":
                    if p["price_inr"] > value:
                        return False
                elif p.get(key) != value:
                    return False
            return True
        hits = [p for p in self.products if _ok(p)]
        hits.sort(key=lambda p: p["price_inr"])
        return hits[:k]


def test_agent_commits_only_when_stable_and_singleton():
    products = [
        {"product_id": "P1", "category": "sneakers", "colour": "navy",
         "size": "7", "brand": "Loomsy", "price_inr": 4500},
        {"product_id": "P2", "category": "sneakers", "colour": "navy",
         "size": "8", "brand": "Loomsy", "price_inr": 4500},
    ]
    agent = Agent(_FakeTools(products))
    agent.start("t1")
    # Stream a correction request; the agent must NOT commit the first
    # (wrong) size even though all slots fill before the correction.
    words = "navy Loomsy sneakers size 7, no, change that to size 8, under 5000".split()
    committed = None
    for w in words:
        out = agent.observe(w)
        if "commit" in out:
            committed = out["commit"]
    assert committed is None  # correction guard held the commit
    assert agent.finish() == "P2"


def test_agent_commits_early_on_a_plain_request():
    products = [
        {"product_id": "P1", "category": "sneakers", "colour": "navy",
         "size": "7", "brand": "Loomsy", "price_inr": 4500},
    ]
    agent = Agent(_FakeTools(products))
    agent.start("t2")
    words = "navy Loomsy sneakers size 7 under 5000 for the gym today".split()
    committed = None
    for w in words:
        out = agent.observe(w)
        if "commit" in out:
            committed = out["commit"]
    assert committed == "P1"
    assert agent.finish() == "P1"
