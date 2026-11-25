"""Anticipatory preference inference.

This is the core of Challenge 1 (Anticipatory Commerce): the shopper's
request is usually incomplete, so the agent must infer the preferences the
shopper did NOT state — from the recipient, the occasion, the use case and
the context — and then act on them, instead of interrogating the shopper
with twenty questions.

Every inference is a transparent, auditable rule with a stated reason, so
the agent can explain *why* it recommended something (and the shopper can
correct it). The agent asks at most ONE clarifying question, and only when
the request is so open that no category can be inferred at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .intent import Intent

# Inference rules: (condition, inferred preferences, reason shown to the user)
# Preferences are (key, weight) pairs; weights sum to ~1.0 per request.


@dataclass
class PreferenceProfile:
    category: str | None = None
    budget: int | None = None
    budget_explicit: bool = True  # False when the budget is an assumed default
    prefs: dict = field(default_factory=dict)   # preference key -> weight
    reasons: list = field(default_factory=list)  # human-readable explanations
    needs_clarification: str | None = None


# Default budgets (INR) when the shopper gives no number, by category.
DEFAULT_BUDGET = {
    "phones": 15000, "laptops": 45000, "audio": 2000, "wearables": 2500,
    "home-kitchen": 3000, "fashion": 1500, "fitness": 1500, "study": 1000,
}

# When no category is stated, the recipient/occasion suggests one.
CATEGORY_BY_RECIPIENT = {
    "mom": ("fashion", "Mothers usually appreciate something wearable or for the home"),
    "dad": ("fashion", "Fathers usually appreciate something practical and wearable"),
    "girlfriend": ("fashion", "A personal, wearable gift usually lands best"),
    "boyfriend": ("fashion", "A personal, wearable gift usually lands best"),
    "wife": ("fashion", "A personal, wearable gift usually lands best"),
    "husband": ("fashion", "A personal, wearable gift usually lands best"),
    "teacher": ("study", "Teachers usually appreciate something useful for their desk"),
    "baby": ("fitness", "Babies need soft, safe, practical things"),
}


def infer_preferences(intent: Intent) -> PreferenceProfile:
    prof = PreferenceProfile(category=intent.category, budget=intent.budget,
                             budget_explicit=intent.budget_explicit)
    prefs: dict[str, float] = {}

    def add(key: str, weight: float, reason: str):
        prefs[key] = prefs.get(key, 0.0) + weight
        prof.reasons.append(reason)

    # --- 1. Category inference when the request names none ------------------
    if prof.category is None:
        if intent.recipient in CATEGORY_BY_RECIPIENT:
            cat, why = CATEGORY_BY_RECIPIENT[intent.recipient]
            prof.category = cat
            add("inferred_category", 0.0, f"No category stated — inferred {cat}: {why.lower()}")
        elif "something" in intent.raw.lower() or "anything" in intent.raw.lower():
            prof.needs_clarification = (
                "Your request is very open — could you tell me who it is for, "
                "or what kind of thing (phone, gift, home, fitness)? "
                "I have still picked my best guess below."
            )
            prof.category = "fashion"  # safe default: most giftable
            add("inferred_category", 0.0, "No category at all — defaulted to fashion (most giftable)")

    # --- 2. Budget default (soft assumption — NEVER a hard filter) -----------
    if prof.budget is None and prof.category in DEFAULT_BUDGET:
        prof.budget = DEFAULT_BUDGET[prof.category]
        prof.budget_explicit = False
        add("budget_default", 0.0,
            f"No budget stated — assumed a typical ₹{prof.budget:,} budget for {prof.category}")

    # --- 3. Recipient-driven anticipation -----------------------------------
    if intent.recipient == "mom":
        add("comfort", 0.25, "For mom: comfort and ease of use matter more than specs")
        add("simple", 0.20, "For mom: simple to use, no complicated setup")
        add("durable", 0.15, "For mom: something that lasts")
    elif intent.recipient == "dad":
        add("durable", 0.25, "For dad: durable and practical wins")
        add("comfort", 0.15, "For dad: comfort matters")
    elif intent.recipient in ("girlfriend", "boyfriend", "wife", "husband"):
        add("premium", 0.20, "For a partner: presentation and quality matter")
        add("popular", 0.15, "For a partner: well-reviewed, well-liked picks are safer")
    elif intent.recipient == "friend":
        add("popular", 0.25, "For a friend: popular, well-reviewed picks are the safe bet")
        add("value", 0.15, "For a friend: good value for money")
    elif intent.recipient == "teacher":
        add("durable", 0.20, "For a teacher: practical and long-lasting")
        add("value", 0.15, "For a teacher: useful, not flashy")
    elif intent.recipient in ("baby",):
        add("comfort", 0.30, "For a baby: soft, safe and comfortable above all")
        add("durable", 0.15, "For a baby: must survive daily use")
    # Gender fit for gifts: dad/brother/husband/boyfriend -> menswear,
    # mom/sister/wife/girlfriend -> womenswear.
    if intent.recipient in ("dad", "father", "brother", "husband", "boyfriend"):
        add("menswear", 0.30, "For him — preferring menswear")
    elif intent.recipient in ("mom", "mother", "sister", "wife", "girlfriend"):
        add("womenswear", 0.30, "For her — preferring womenswear")

    # --- 4. Occasion-driven anticipation ------------------------------------
    if intent.occasion in ("birthday", "anniversary", "valentine"):
        add("premium", 0.15, f"{intent.occasion.title()}: a slightly premium pick feels special")
        add("popular", 0.10, f"{intent.occasion.title()}: well-loved picks are safer gifts")
    elif intent.occasion == "diwali":
        add("festive", 0.25, "Diwali: festive, auspicious, family-friendly picks")
        add("premium", 0.10, "Diwali: gifting season — a touch premium is expected")
    elif intent.occasion == "wedding":
        add("premium", 0.25, "Wedding: premium, presentable, traditional-leaning")
    elif intent.occasion in ("rakhi", "housewarming", "graduation", "farewell"):
        add("value", 0.15, f"{intent.occasion.title()}: thoughtful value beats flash")
        add("durable", 0.10, f"{intent.occasion.title()}: something that lasts")

    # --- 5. Use-case-driven anticipation ------------------------------------
    if "gaming" in intent.use_cases:
        add("performance", 0.30, "Gaming: performance (chip/GPU/RAM) is the deciding factor")
    if "creator" in intent.use_cases:
        add("performance", 0.25, "Editing/creation: a strong chip/GPU and RAM matter most")
    if "coding" in intent.use_cases:
        add("performance", 0.20, "Coding: RAM and a good keyboard matter most")
        add("lightweight", 0.10, "Coding: light enough to carry to class")
    if "study" in intent.use_cases:
        add("value", 0.20, "Study: best value for a student budget")
        add("battery", 0.15, "Study: long battery for full days of classes")
    if "running" in intent.use_cases or "gym" in intent.use_cases:
        add("durable", 0.20, "Fitness: must survive sweat, drops and daily use")
        add("waterproof", 0.15, "Fitness: sweat/water resistance matters")
    if "travel" in intent.use_cases:
        add("lightweight", 0.25, "Travel: light and compact wins")
        add("battery", 0.15, "Travel: long battery, no charger anxiety")
    if "office" in intent.use_cases:
        add("premium", 0.15, "Office: neat, professional, presentable")
        add("durable", 0.10, "Office: built to last daily use")
    if "hostel" in intent.use_cases:
        add("lightweight", 0.15, "Hostel: compact, fits a small room")
        add("value", 0.15, "Hostel: best value on a student budget")
    if "monsoon" in intent.use_cases:
        add("waterproof", 0.30, "Monsoon: water resistance is non-negotiable")
    if "winter" in intent.use_cases:
        add("comfort", 0.25, "Winter: warmth and comfort first")
    if "summer" in intent.use_cases:
        add("comfort", 0.20, "Summer: cooling and comfort first")

    # --- 6. Explicitly stated attributes ------------------------------------
    for attr in intent.attributes:
        add(attr, 0.25, f"You asked for {attr} — weighted heavily")

    # --- 7. Gift defaults ----------------------------------------------------
    if intent.is_gift and not intent.attributes and not intent.use_cases:
        add("popular", 0.15, "Gift with no details: popular, well-reviewed picks are safest")
        add("value", 0.10, "Gift with no details: good value, no regret")

    # Normalise weights to sum to 1.0 (ignoring zero-weight bookkeeping keys).
    scored = {k: v for k, v in prefs.items() if v > 0}
    total = sum(scored.values()) or 1.0
    prof.prefs = {k: round(v / total, 3) for k, v in scored.items()}
    return prof
