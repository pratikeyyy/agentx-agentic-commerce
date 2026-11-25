"""Sauda Bazaar — product catalog (simulated demo catalog).

The catalog is a representative Indian-market product list used for the
demo and the development-set evaluation. It is NOT a live store: prices,
stock and ratings are representative values for demonstration.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "products.json")


@dataclass
class Product:
    id: str
    name: str
    brand: str
    category: str
    price: int
    mrp: int
    rating: float
    reviews: int
    stock: int
    desc: str
    tags: list = field(default_factory=list)
    attrs: dict = field(default_factory=dict)

    @property
    def discount_pct(self) -> float:
        return round(100 * (self.mrp - self.price) / self.mrp, 1) if self.mrp > self.price else 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "brand": self.brand,
            "category": self.category, "price": self.price, "mrp": self.mrp,
            "rating": self.rating, "reviews": self.reviews, "stock": self.stock,
            "desc": self.desc, "tags": self.tags, "attrs": self.attrs,
            "discount_pct": self.discount_pct,
        }


class Catalog:
    def __init__(self, path: str = CATALOG_PATH):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.store = data.get("store", "Sauda Bazaar")
        self.products = [Product(**p) for p in data["products"]]
        self.by_id = {p.id: p for p in self.products}

    def get(self, product_id: str) -> Product | None:
        return self.by_id.get(product_id)

    def by_category(self, category: str) -> list[Product]:
        return [p for p in self.products if p.category == category]

    def search(self, text: str, limit: int = 20) -> list[Product]:
        """Simple keyword search over name/brand/tags/description."""
        words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2]
        scored = []
        for p in self.products:
            hay = f"{p.name} {p.brand} {p.category} {' '.join(p.tags)} {p.desc}".lower()
            hits = sum(1 for w in words if w in hay)
            if hits:
                scored.append((hits, p.rating, p))
        scored.sort(key=lambda t: (-t[0], -t[1]))
        return [p for _, _, p in scored[:limit]]

    def in_budget(self, category: str, budget: int) -> list[Product]:
        return [p for p in self.products if p.category == category and p.price <= budget]

    def categories(self) -> list[str]:
        return sorted({p.category for p in self.products})
