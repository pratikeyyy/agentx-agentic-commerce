"""Intent parsing for incomplete shopping requests.

Real shoppers rarely write complete specs. They write things like:
  "gift for mom under 2000"        (no category, no product type)
  "phone under 15000 with good camera"
  "something for my room"
  "laptop for coding"
The parser extracts what IS said — category, budget, recipient, occasion,
must-have attributes — and leaves the rest for the anticipatory layer
(preferences.py), which infers what was NOT said.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- keyword maps -----------------------------------------------------------

CATEGORY_KEYWORDS = {
    "phones": ["phone", "mobile", "smartphone", "iphone", "android", "handset"],
    "laptops": ["laptop", "macbook", "notebook", "ultrabook"],
    "audio": ["earbuds", "earphone", "headphone", "headset", "tws", "buds",
              "speaker", "neckband", "airpods", "earpods"],
    "wearables": ["smartwatch", "watch", "fitness band", "fitbit", "band"],
    "home-kitchen": ["mixer", "grinder", "cooker", "kettle", "microwave", "oven",
                     "air fryer", "fryer", "blender", "iron", "bottle", "tawa",
                     "casserole", "dinner set", "fan", "cooler", "chair", "table",
                     "mattress", "safe", "locker", "kitchen", "home"],
    "fashion": ["saree", "sari", "kurta", "kurti", "t-shirt", "tshirt", "jeans",
                "shoes", "sneakers", "dress", "sweater", "shirt", "clothes",
                "fashion", "wear", "outfit", "footwear"],
    "fitness": ["dumbbell", "dumbell", "yoga mat", "resistance band", "gym",
                "pull-up", "pullup", "skipping rope", "barbell", "football",
                "cricket bat", "workout", "exercise"],
    "study": ["calculator", "notebook", "pen", "pencil", "desk lamp", "lamp",
              "backpack", "bag", "power bank", "mouse", "keyboard", "printer",
              "geometry box", "watercolour", "aa battery", "clock", "pen drive",
              "hard drive", "hdd", "cable", "stationery", "study"],
}

RECIPIENT_KEYWORDS = {
    "mom": ["mom", "mother", "mummy", "amma", "maa"],
    "dad": ["dad", "father", "papa", "daddy"],
    "brother": ["brother", "bhai"],
    "sister": ["sister", "behen", "didi"],
    "friend": ["friend", "bestie", "buddy"],
    "girlfriend": ["girlfriend", "gf"],
    "boyfriend": ["boyfriend", "bf"],
    "wife": ["wife", "biwi"],
    "husband": ["husband", "pati"],
    "teacher": ["teacher", "professor", "sir", "ma'am", "mam"],
    "self": ["for me", "for myself", "my own", "i need", "i want"],
    "baby": ["baby", "kid", "child", "son", "daughter", "bacha"],
}

OCCASION_KEYWORDS = {
    "birthday": ["birthday", "bday"],
    "diwali": ["diwali", "deepavali"],
    "wedding": ["wedding", "shaadi", "marriage"],
    "anniversary": ["anniversary"],
    "rakhi": ["rakhi", "raksha bandhan"],
    "valentine": ["valentine", "valentines"],
    "housewarming": ["housewarming", "griha pravesh", "new home"],
    "graduation": ["graduation", "convocation"],
    "farewell": ["farewell"],
    "christmas": ["christmas"],
    "new year": ["new year"],
}

ATTRIBUTE_SIGNALS = {
    "camera": ["camera", "photo", "photography", "picture"],
    "battery": ["battery", "backup", "long lasting", "long-lasting", "charge"],
    "performance": ["fast", "gaming", "performance", "speed", "processor", "chip"],
    "display": ["display", "screen", "amoled", "oled", "big screen"],
    "lightweight": ["light", "lightweight", "portable", "carry"],
    "storage": ["storage", "space", "memory", "gb"],
    "sound": ["sound", "bass", "music", "audio"],
    "anc": ["anc", "noise cancelling", "noise cancellation", "noise-cancelling"],
    "waterproof": ["waterproof", "water resistant", "sweat", "rain"],
    "comfort": ["comfort", "comfortable", "soft", "easy"],
    "durable": ["durable", "strong", "tough", "long lasting"],
    "premium": ["premium", "best", "top", "flagship", "branded"],
    "cheap": ["cheap", "cheapest", "low price", "sasta"],
}

USE_CASE_SIGNALS = {
    "gaming": ["gaming", "game", "bgmi", "pubg", "fps"],
    "coding": ["coding", "programming", "code", "developer", "ml", "ai", "python"],
    "creator": ["editing", "video editing", "creator", "design", "designing"],
    "study": ["study", "college", "school", "exam", "classes", "assignment"],
    "running": ["running", "run", "jogging", "marathon"],
    "gym": ["gym", "workout", "exercise", "training"],
    "travel": ["travel", "trip", "trek", "trekking", "tour"],
    "office": ["office", "work", "meeting", "job", "interview"],
    "music": ["music", "song", "listen"],
    "calls": ["calls", "calling", "meeting"],
    "hostel": ["hostel", "pg", "room", "dorm"],
    "monsoon": ["monsoon", "rain", "rainy"],
    "winter": ["winter", "cold"],
    "summer": ["summer", "heat", "hot"],
}

_BUDGET_RE = re.compile(
    r"(?:under|below|less than|up ?to|max(?:imum)?|budget(?: of)?|within|around|rs\.?|inr|₹)\s*"
    r"(\d[\d,]*)(\s*k)?",
    re.IGNORECASE,
)
_BARE_BUDGET_RE = re.compile(r"(\d[\d,]{3,})\s*(?:rupees|rs\b|inr|₹)?", re.IGNORECASE)


@dataclass
class Intent:
    raw: str
    category: str | None = None
    category_confidence: float = 0.0
    budget: int | None = None
    budget_explicit: bool = False  # True only when the shopper stated a number
    recipient: str | None = None
    occasion: str | None = None
    attributes: list = field(default_factory=list)
    use_cases: list = field(default_factory=list)
    is_gift: bool = False
    notes: list = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return bool(self.category and self.budget)


def _find(text: str, table: dict[str, list[str]]) -> str | None:
    """Best category by keyword hits (more hits wins; longer keywords win ties)."""
    best, best_score = None, 0
    for key, words in table.items():
        hits = 0
        longest = 0
        for w in words:
            if re.search(rf"\b{re.escape(w)}s?\b", text):
                hits += 1
                longest = max(longest, len(w))
        score = hits * 10 + longest
        if score > best_score:
            best, best_score = key, score
    return best


def _find_all(text: str, table: dict[str, list[str]]) -> list[str]:
    found = []
    for key, words in table.items():
        if any(re.search(rf"\b{re.escape(w)}s?\b", text) for w in words):
            found.append(key)
    return found


def _parse_budget(text: str) -> int | None:
    m = _BUDGET_RE.search(text)
    if m:
        value = int(m.group(1).replace(",", ""))
        if m.group(2):  # "15k"
            value *= 1000
        if 50 <= value <= 500_000:
            return value
    return None


def parse_intent(raw: str) -> Intent:
    text = raw.lower().strip()
    intent = Intent(raw=raw)

    # Category: explicit keywords first; "gift" alone gives no category.
    intent.category = _find(text, CATEGORY_KEYWORDS)
    if intent.category:
        intent.category_confidence = 0.9
    elif "gift" in text or "present" in text:
        intent.notes.append("no category stated — gift request, category must be inferred")

    intent.budget = _parse_budget(text)
    if intent.budget is None:
        m = _BARE_BUDGET_RE.search(text)
        if m:
            v = int(m.group(1).replace(",", ""))
            if 100 <= v <= 500_000:
                intent.budget = v
                intent.notes.append("budget inferred from bare number")
    intent.budget_explicit = intent.budget is not None

    intent.recipient = _find(text, RECIPIENT_KEYWORDS)
    intent.occasion = _find(text, OCCASION_KEYWORDS)
    intent.attributes = _find_all(text, ATTRIBUTE_SIGNALS)
    intent.use_cases = _find_all(text, USE_CASE_SIGNALS)
    intent.is_gift = bool(re.search(r"\bgift\b|\bpresent\b|\bfor (mom|dad|mother|father|friend|sister|brother)\b", text))
    return intent
