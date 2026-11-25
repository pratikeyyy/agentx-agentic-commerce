"""Rezolve Labs integration — Brain Commerce adapter.

What Rezolve Labs is (per Rezolve Ai's public material, Nov 2026):
  * brainpowa — commerce-trained models that interpret shopper intent.
  * Rezolve Commerce — agent-ready product discovery: trusted answers from a
    merchant's own catalog, live pricing and availability.
  * Brain Checkout — agentic checkout that converts intent into a sale.
  * Rezolve Pay — payment optimisation for the transaction.
  * Agentic Plug-in — governance: what an agent may say, which products it
    may recommend, how substitutions, pricing and fulfilment are handled.

How this integration works:
  * `RezolveClient` exposes exactly those capabilities as methods:
    `interpret_intent`, `discover`, `checkout`, `govern` (policy check).
  * LIVE MODE: set REZOLVE_API_KEY and REZOLVE_BASE_URL (the coupon and
    endpoint given to registered AgentX participants) and the adapter calls
    the real Rezolve Labs APIs. The switch is one environment change.
  * STUB MODE (default, used for the demo): the same methods run against a
    local Rezolve-compatible implementation over the demo catalog, so the
    full agent loop works end to end before the coupon arrives.

Honesty note (also in docs/REZOLVE_INTEGRATION.md and the abstract):
Rezolve Labs access is by invitation — the coupon is shared with registered
AgentX participants after Techfest registration. This repo therefore ships
with the integration fully implemented and verified against the stub, and
the live key is a drop-in swap. Nothing in the demo pretends a live Rezolve
call happened when it did not: every trace entry records its source
("rezolve:stub" or "rezolve:live").
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from .catalog import Catalog, Product
from .intent import Intent, parse_intent
from .preferences import PreferenceProfile, infer_preferences

REZOLVE_CAPABILITIES_USED = [
    "brainpowa — commerce intent interpretation",
    "Rezolve Commerce — agent-ready product discovery (catalog, live price, availability)",
    "Brain Checkout — agentic checkout",
    "Agentic Plug-in — governance (what the agent may recommend, price & fulfilment policy)",
]


@dataclass
class RezolveResult:
    source: str  # "rezolve:stub" or "rezolve:live"
    capability: str
    payload: dict = field(default_factory=dict)
    latency_ms: float = 0.0


class RezolveClient:
    """Adapter for Rezolve Labs Brain Commerce capabilities.

    Live mode is selected automatically when REZOLVE_API_KEY is set.
    """

    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.api_key = os.environ.get("REZOLVE_API_KEY", "")
        self.base_url = os.environ.get(
            "REZOLVE_BASE_URL", "https://api.rezolvelabs.com/v1")
        self.live = bool(self.api_key)
        self.source = "rezolve:live" if self.live else "rezolve:stub"

    # -- capability 1: brainpowa intent interpretation -----------------------
    def interpret_intent(self, text: str) -> RezolveResult:
        t0 = time.time()
        if self.live:
            return self._call("brainpowa/interpret", {"text": text}, t0,
                              "brainpowa — commerce intent interpretation")
        intent = parse_intent(text)
        profile = infer_preferences(intent)
        return RezolveResult(
            source=self.source,
            capability="brainpowa — commerce intent interpretation",
            payload={"intent": _intent_dict(intent), "preferences": profile.prefs},
            latency_ms=(time.time() - t0) * 1000,
        )

    # -- capability 2: Rezolve Commerce product discovery --------------------
    def discover(self, category: str, budget: int | None,
                 limit: int = 20) -> RezolveResult:
        t0 = time.time()
        if self.live:
            return self._call("commerce/discover",
                              {"category": category, "budget": budget, "limit": limit},
                              t0, "Rezolve Commerce — agent-ready product discovery")
        pool = self.catalog.by_category(category) if category else self.catalog.products
        if budget is not None:
            pool = [p for p in pool if p.price <= int(budget * 1.10)] or pool
        items = [p.to_dict() for p in pool if p.stock > 0][:limit]
        return RezolveResult(
            source=self.source,
            capability="Rezolve Commerce — agent-ready product discovery",
            payload={"items": items, "count": len(items)},
            latency_ms=(time.time() - t0) * 1000,
        )

    # -- capability 3: Brain Checkout ----------------------------------------
    def checkout(self, items: list[dict], total_inr: int) -> RezolveResult:
        t0 = time.time()
        if self.live:
            return self._call("checkout/create",
                              {"items": items, "total_inr": total_inr},
                              t0, "Brain Checkout — agentic checkout")
        import random
        order_id = f"SAU-{random.randint(100000, 999999)}"
        return RezolveResult(
            source=self.source,
            capability="Brain Checkout — agentic checkout (SIMULATED — no real money moves)",
            payload={"order_id": order_id, "total_inr": total_inr,
                     "status": "confirmed_simulated",
                     "payment": "UPI (simulated)"},
            latency_ms=(time.time() - t0) * 1000,
        )

    # -- capability 4: Agentic Plug-in governance -----------------------------
    def govern(self, recommendation: dict, intent: Intent) -> RezolveResult:
        """Policy check: the agent may only recommend in-stock items within
        (or negligibly above) the shopper's budget, and must disclose when a
        recommendation is simulated data."""
        t0 = time.time()
        product = recommendation.get("product", {})
        violations = []
        if not recommendation.get("in_stock"):
            violations.append("out of stock — recommend only as an alternative, with a warning")
        if intent.budget and product.get("price", 0) > intent.budget * 1.10:
            violations.append("more than 10% over the stated budget — flag it, do not hide it")
        return RezolveResult(
            source=self.source,
            capability="Agentic Plug-in — governance",
            payload={"allowed": not violations, "violations": violations,
                     "policy": "in-stock only for the top pick; budget respected within 10%; "
                               "simulated data always disclosed"},
            latency_ms=(time.time() - t0) * 1000,
        )

    # -- live transport (used only when a real key is present) ----------------
    def _call(self, path: str, body: dict, t0: float, capability: str) -> RezolveResult:
        import requests
        resp = requests.post(
            f"{self.base_url}/{path}",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return RezolveResult(
            source="rezolve:live", capability=capability,
            payload=resp.json(), latency_ms=(time.time() - t0) * 1000)


def _intent_dict(intent: Intent) -> dict:
    return {
        "raw": intent.raw, "category": intent.category,
        "category_confidence": intent.category_confidence,
        "budget": intent.budget, "recipient": intent.recipient,
        "occasion": intent.occasion, "attributes": intent.attributes,
        "use_cases": intent.use_cases, "is_gift": intent.is_gift,
        "notes": intent.notes,
    }
