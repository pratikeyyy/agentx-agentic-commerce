"""Sauda — the anticipatory shopping agent (Challenge 1: Anticipatory Commerce).

One run of the agent, visible step by step (the trace is shown in the UI
and the demo video):

  1. UNDERSTAND   — parse the incomplete request (Rezolve brainpowa).
  2. ANTICIPATE   — infer the preferences the shopper did NOT state.
  3. DISCOVER     — pull candidate products (Rezolve Commerce).
  4. RANK         — score and shortlist the top 3.
  5. GOVERN       — policy check (Agentic Plug-in): in-stock, in-budget.
  6. RECOMMEND    — one primary pick, with the reasons, plus 2 alternatives.
  7. CHECKOUT     — only when the shopper confirms (simulated).

The agent asks at most ONE clarifying question, and only when no category
can be inferred at all — and it still produces a best-guess recommendation
in the same reply, so the shopper is never left empty-handed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .catalog import Catalog
from .intent import Intent, parse_intent
from .preferences import PreferenceProfile, infer_preferences
from .ranking import rank
from .rezolve import RezolveClient


@dataclass
class TraceStep:
    step: str
    title: str
    detail: str
    source: str
    ms: float

    def to_dict(self) -> dict:
        return {"step": self.step, "title": self.title, "detail": self.detail,
                "source": self.source, "ms": round(self.ms, 1)}


@dataclass
class AgentRun:
    query: str
    intent: Intent
    profile: PreferenceProfile
    recommendations: list
    primary: dict | None
    comparison: list
    clarifying_question: str | None
    trace: list = field(default_factory=list)
    total_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "intent": {
                "category": self.intent.category,
                "category_confidence": self.intent.category_confidence,
                "budget": self.intent.budget, "recipient": self.intent.recipient,
                "occasion": self.intent.occasion, "attributes": self.intent.attributes,
                "use_cases": self.intent.use_cases, "is_gift": self.intent.is_gift,
                "notes": self.intent.notes,
            },
            "inferred_preferences": self.profile.prefs,
            "inference_reasons": self.profile.reasons,
            "recommendations": self.recommendations,
            "primary": self.primary,
            "comparison": self.comparison,
            "clarifying_question": self.clarifying_question,
            "budget_explicit": self.profile.budget_explicit,
            "trace": [t.to_dict() for t in self.trace],
            "total_ms": round(self.total_ms, 1),
        }


class SaudaAgent:
    def __init__(self, catalog: Catalog | None = None):
        self.catalog = catalog or Catalog()
        self.rezolve = RezolveClient(self.catalog)

    def run(self, query: str) -> AgentRun:
        t0 = time.time()
        trace: list[TraceStep] = []

        # 1. UNDERSTAND (Rezolve brainpowa)
        s = time.time()
        intent_res = self.rezolve.interpret_intent(query)
        intent = parse_intent(query)
        profile = infer_preferences(intent)
        trace.append(TraceStep(
            "understand", "Understand the request",
            f"Category: {intent.category or 'not stated'} · "
            f"Budget: {'₹' + format(intent.budget, ',') + (' (stated)' if intent.budget_explicit else ' (assumed)') if intent.budget else 'not stated'} · "
            f"Recipient: {intent.recipient or '—'} · Occasion: {intent.occasion or '—'}",
            intent_res.source, (time.time() - s) * 1000))

        # 2. ANTICIPATE (preferences the shopper did not state)
        s = time.time()
        top_prefs = ", ".join(
            f"{k} ({v:.0%})" for k, v in
            sorted(profile.prefs.items(), key=lambda kv: -kv[1])[:3])
        trace.append(TraceStep(
            "anticipate", "Anticipate unstated preferences",
            top_prefs or "no strong inferred preferences",
            "sauda:preferences", (time.time() - s) * 1000))

        # 3. DISCOVER (Rezolve Commerce)
        s = time.time()
        disc = self.rezolve.discover(profile.category, profile.budget)
        trace.append(TraceStep(
            "discover", "Discover products",
            f"{disc.payload.get('count', 0)} in-stock candidates in "
            f"{profile.category or 'all categories'}",
            disc.source, (time.time() - s) * 1000))

        # 4. RANK
        s = time.time()
        ranked = rank(self.catalog, profile, query, limit=3)
        trace.append(TraceStep(
            "rank", "Rank and shortlist",
            "Top 3 by text relevance (30) + attribute fit (25) + value (20) + "
            "budget fit (15) + preference fit (10)",
            "sauda:ranking", (time.time() - s) * 1000))

        # 5. GOVERN (Agentic Plug-in) + 6. RECOMMEND
        s = time.time()
        primary = ranked[0] if ranked else None
        gov = self.rezolve.govern(primary or {}, intent) if primary else None
        if gov is not None:
            trace.append(TraceStep(
                "govern", "Policy check (Agentic Plug-in)",
                "Allowed" if gov.payload.get("allowed")
                else "Flagged: " + "; ".join(gov.payload.get("violations", [])),
                gov.source, (time.time() - s) * 1000))

        # Build human-readable reasons for the primary pick.
        recommendations = []
        for i, r in enumerate(ranked):
            p = r["product"]
            reasons = []
            if r["breakdown"]["attribute_fit"] >= 0.6:
                reasons.append("matches what you asked for")
            if profile.prefs:
                top_pref = max(profile.prefs, key=profile.prefs.get)
                reasons.append(f"fits your unstated need: {top_pref}")
            if r["breakdown"]["value"] >= 0.6:
                reasons.append(f"great value — {p['rating']}★ from {p['reviews']:,} reviews")
            if r["over_budget"]:
                reasons.append(f"₹{p['price'] - (profile.budget or 0):,} over your budget — flagged, not hidden")
            if not r["in_stock"]:
                reasons.append("OUT OF STOCK — shown only as an alternative")
            recommendations.append({
                "rank": i + 1, "product": p, "score": r["score"],
                "breakdown": r["breakdown"], "reasons": reasons,
                "over_budget": r["over_budget"], "in_stock": r["in_stock"],
            })

        comparison = [
            {"name": r["product"]["name"], "price": r["product"]["price"],
             "rating": r["product"]["rating"], "score": r["score"],
             "key_spec": _key_spec(r["product"])}
            for r in ranked
        ]

        return AgentRun(
            query=query, intent=intent, profile=profile,
            recommendations=recommendations,
            primary=recommendations[0] if recommendations else None,
            comparison=comparison,
            clarifying_question=profile.needs_clarification,
            trace=trace,
            total_ms=(time.time() - t0) * 1000,
        )


def _key_spec(product: dict) -> str:
    a = product.get("attrs", {})
    bits = []
    if a.get("ram_gb"):
        bits.append(f"{a['ram_gb']}GB RAM")
    if a.get("storage_gb"):
        bits.append(f"{a['storage_gb']}GB")
    if a.get("camera_mp"):
        bits.append(f"{a['camera_mp']}MP camera")
    if a.get("battery_mah"):
        bits.append(f"{a['battery_mah']}mAh")
    if a.get("battery_h"):
        bits.append(f"{a['battery_h']}h battery")
    if a.get("anc"):
        bits.append("ANC")
    if a.get("gps"):
        bits.append("GPS")
    return " · ".join(bits) if bits else product.get("desc", "")[:60]
