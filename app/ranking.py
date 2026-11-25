"""Product ranking: turn an incomplete request into a scored shortlist.

Scoring (0-100 per product):
  30 pts  text relevance — request keywords vs product name/tags/desc
  25 pts  attribute fit — stated attributes (camera, battery, RAM, ...) and
          inferred preferences, matched against product specs
  20 pts  value — rating, review volume, discount
  15 pts  budget fit — full marks inside budget; the top pick is NEVER over
          budget when an in-budget option exists (over-budget items appear
          only as flagged alternatives)
  10 pts  preference fit — inferred needs (comfort, durability, premium feel)
Plus small honest bonuses: "cheapest" requests rank by price; gaming/creator
requests favour products with a real GPU (RTX/GTX).
"""
from __future__ import annotations

import math
import re

from .catalog import Catalog, Product
from .preferences import PreferenceProfile

ATTR_MAP = {
    "camera": ("camera_mp", 1.0),
    "battery": ("battery", 1.0),          # battery_mah or battery_h (see below)
    "performance": ("ram_gb", 0.6),
    "display": ("screen_in", 0.5),
    "lightweight": ("weight_g", -1.0),    # lower is better
    "storage": ("storage_gb", 1.0),
    "sound": ("rating", 0.3),
    "anc": ("anc", 1.0),
    "waterproof": ("waterproof", 1.0),
    "durable": ("rating", 1.0),          # durable == well-reviewed / high-rated
}

STOPWORDS = {
    "for", "under", "with", "the", "and", "good", "best", "my", "a", "an",
    "in", "of", "to", "me", "i", "want", "need", "need", "please", "something",
    "anything", "gift", "present", "buy", "looking", "show", "give", "is",
    "it", "this", "that", "from", "near", "around", "below", "less", "than",
    "max", "maximum", "budget", "rs", "inr", "rupees", "mom", "dad", "mother",
    "father", "friend", "sister", "brother", "wife", "husband", "girlfriend",
    "boyfriend", "teacher", "baby", "kid", "child",
}


def query_tokens(query: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", query.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS
            and not w.isdigit()]


def _relevance(product: Product, tokens: list[str]) -> float:
    """0-1: request keywords vs name (3) / tags (2) / desc+brand (1)."""
    if not tokens:
        return 0.5
    name = product.name.lower()
    tags = " ".join(product.tags).lower()
    other = f"{product.desc} {product.brand}".lower()
    score, max_score = 0, 0
    for tok in tokens:
        max_score += 3
        if tok in name:
            score += 3
        elif tok in tags:
            score += 2
        elif tok in other:
            score += 1
    return score / max_score


def _norm(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.5
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _battery_value(product: Product) -> float | None:
    """Battery capacity in mAh-equivalent (battery_h scaled x1000)."""
    if isinstance(product.attrs.get("battery_mah"), (int, float)):
        return float(product.attrs["battery_mah"])
    if isinstance(product.attrs.get("battery_h"), (int, float)):
        return float(product.attrs["battery_h"]) * 1000
    return None


def _attr_score(product: Product, prefs: dict, catalog: Catalog) -> float:
    total_w, weighted = 0.0, 0.0
    same_cat = catalog.by_category(product.category)
    for key, weight in prefs.items():
        if key not in ATTR_MAP or weight <= 0:
            continue
        attr, direction = ATTR_MAP[key]
        if attr == "rating":
            # "rating" is a product field, not an attrs entry.
            s = _norm(product.rating, 3.5, 5.0)
            weighted += weight * s
            total_w += weight
            continue
        if attr == "battery":
            vals = [v for v in (_battery_value(p) for p in same_cat) if v is not None]
            v = _battery_value(product)
            if not vals or v is None:
                s = 0.3
            else:
                s = _norm(v, min(vals), max(vals))
            weighted += weight * s
            total_w += weight
            continue
        vals = [p.attrs.get(attr) for p in same_cat
                if isinstance(p.attrs.get(attr), (int, float))]
        if not vals:
            has = bool(product.attrs.get(attr))
            weighted += weight * (1.0 if has else 0.2)
            total_w += weight
            continue
        v = product.attrs.get(attr)
        s = 0.3 if v is None else _norm(float(v), min(vals), max(vals))
        if direction < 0:
            s = 1.0 - s
        weighted += weight * s
        total_w += weight
    return weighted / total_w if total_w else 0.5


def _value_score(product: Product) -> float:
    rating = _norm(product.rating, 3.5, 5.0)
    reviews = _norm(math.log10(max(product.reviews, 1)), 3.0, 5.5)
    discount = _norm(product.discount_pct, 0, 50)
    return 0.5 * rating + 0.3 * reviews + 0.2 * discount


def _preference_fit(product: Product, prefs: dict) -> float:
    s, total = 0.0, 0.0
    if prefs.get("comfort"):
        s += prefs["comfort"] * _norm(product.rating, 4.0, 4.8); total += prefs["comfort"]
    if prefs.get("durable"):
        s += prefs["durable"] * _norm(product.rating, 4.0, 4.8); total += prefs["durable"]
    if prefs.get("premium"):
        s += prefs["premium"] * _norm(product.price, 1000, 50000); total += prefs["premium"]
    if prefs.get("popular"):
        s += prefs["popular"] * _norm(math.log10(max(product.reviews, 1)), 3.0, 5.5); total += prefs["popular"]
    if prefs.get("value"):
        s += prefs["value"] * _norm(product.discount_pct, 0, 50); total += prefs["value"]
    if prefs.get("simple"):
        s += prefs["simple"] * (1.0 if product.attrs.get("screen_in", 0) >= 6.0 else 0.5); total += prefs["simple"]
    if prefs.get("festive"):
        s += prefs["festive"] * _norm(product.rating, 4.0, 4.8); total += prefs["festive"]
    # Gender fit: a gift for dad should be menswear, for mom womenswear.
    # ("women" is checked first — it contains the substring "men".)
    if prefs.get("menswear") or prefs.get("womenswear"):
        hay = (product.name + " " + " ".join(product.tags)).lower()
        if "women" in hay or "woman" in hay or "girl" in hay:
            g = 0.0
        elif "men" in hay or "boy" in hay:
            g = 1.0
        else:
            g = 0.5
        key = "menswear" if prefs.get("menswear") else "womenswear"
        s += prefs[key] * (g if key == "menswear" else 1.0 - g); total += prefs[key]
    return s / total if total else 0.5


def rank(catalog: Catalog, profile: PreferenceProfile, query: str,
         limit: int = 5) -> list[dict]:
    budget = profile.budget
    # Hard budget rule applies ONLY to a budget the shopper actually stated.
    # An assumed (default) budget is a soft preference, never a filter.
    hard_budget = budget if getattr(profile, "budget_explicit", True) else None
    tokens = query_tokens(query)
    candidates = catalog.by_category(profile.category) if profile.category else catalog.products
    in_budget = [p for p in candidates if hard_budget is None or p.price <= hard_budget]
    pool = in_budget if in_budget else candidates
    prices = [p.price for p in pool]
    lo, hi = min(prices), max(prices)
    scored = []
    for p in pool:
        rel = _relevance(p, tokens)
        a = _attr_score(p, profile.prefs, catalog)
        v = _value_score(p)
        # Budget fit: full marks inside budget. Over an EXPLICIT budget the
        # score is 0 (those items only appear when nothing fits). Over an
        # ASSUMED budget the score fades — but the floor scales with how
        # precisely the shopper named the product (relevance): an exact
        # product name overrides a guessed budget, a vague request respects
        # it. So "apple watch" still finds the Apple Watch, while "phone
        # for mom" does not jump to a phone 3.5x over the typical budget.
        if budget is None:
            b = 1.0
        elif p.price <= budget:
            b = 1.0
        elif getattr(profile, "budget_explicit", True):
            b = 0.0
        else:
            # Assumed budget: the floor scales with how precisely the
            # shopper named the product (relevance): an exact product name
            # overrides a guessed budget, a vague request respects it. The
            # fade is steep — a mild overage is forgiven, a 2x+ overage is
            # not — so "phone for mom" does not jump to a phone 3.5x over
            # the typical budget, while "apple watch" still finds the
            # Apple Watch.
            floor = 0.9 * max(0.0, (rel - 0.5) / 0.5)
            fade = max(0.0, 1.0 - (p.price - budget) / (0.5 * budget))
            b = max(floor, fade)
        f = _preference_fit(p, profile.prefs)
        total = 30 * rel + 25 * a + 20 * v + 15 * b + 10 * f
        # "cheapest" requests rank by price — decisively, since the shopper
        # asked for the cheapest, not merely a good-value option.
        if profile.prefs.get("cheap"):
            total += 25 * (1 - _norm(p.price, lo, hi))
        # Gaming / creator requests favour a real GPU.
        if profile.prefs.get("performance") and ("rtx" in p.name.lower() or "gtx" in p.name.lower()):
            total += 8
        scored.append({
            "product": p.to_dict(),
            "score": round(min(total, 100.0), 1),
            "breakdown": {
                "relevance": round(rel, 2),
                "attribute_fit": round(a, 2),
                "value": round(v, 2),
                "budget_fit": round(b, 2),
                "preference_fit": round(f, 2),
            },
            "over_budget": bool(hard_budget and p.price > hard_budget),
            "in_stock": p.stock > 0,
        })
    scored.sort(key=lambda r: (-r["score"], -r["product"]["rating"]))
    top = [r for r in scored if r["in_stock"]][:limit]
    if len(top) < limit:
        top += [r for r in scored if not r["in_stock"]][: limit - len(top)]
    return top
