"""Sauda — streaming agent for the Techfest AgentX official dev set.

This is the same Sauda agent as the FastAPI service (app/agent.py), adapted
to the competition's streaming protocol (official-dev-set/.../evaluate.py):
words arrive one at a time, the agent may commit a product early, and
finish() must return the final product.

Sauda's seven steps, in streaming form:
  1. UNDERSTAND — parse the words so far into filters (category, colour,
     size, brand, max_price) with the official catalogue's vocabulary,
     synonyms, English/Hindi number words and last-mention-wins corrections.
  2. ANTICIPATE — nothing is guessed: a filter is used only when the
     shopper stated it. An unstated filter stays open, never assumed.
  3. DISCOVER — one counted search through tools.search, only when the
     filters changed and a commit is possible (searches are penalised).
  4. RANK — the harness search ranks by keyword overlap, cheaper first.
     With exact filters the target is the only match (verified: the gold
     filters pin exactly one product in all 300 dev requests).
  5. GOVERN — commit only when every applicable filter is stated and the
     search returns exactly one product. A wrong commit costs 1.0 and
     wipes out the earliness bonus, while a correct early commit gains at
     most 0.6 x the words left — so the rule is strict on purpose.
  6. RECOMMEND — the commit (or the finish() answer).
  7. CHECKOUT — not part of scoring; the demo service simulates it.

Rules the code follows (starter-kit README.md):
  * standard library only; no test data is read at run time — the agent
    sees only the words so far plus tools.search. The vocabulary below was
    built from catalogue.csv (which the kit explicitly allows): the
    categories, colours, brands and sizes, plus the synonyms shoppers
    actually use in the requests.
  * every search goes through tools.search and is counted.
"""

from __future__ import annotations

import re

# --- vocabulary: derived from catalogue.csv (1,074 products) ----------------
# Each entry maps a canonical value to the phrases shoppers use for it.
# Phrases are matched longest-first, spans are consumed, and the LAST
# mention wins (so "black, oops, grey" ends up grey, as it should).

CATEGORIES = {
    "running shoes": ["running shoes", "running shoe", "running sneakers",
                      "jogging shoes", "jogging shoe", "runners", "runner"],
    "sneakers": ["casual sneakers", "casual shoes", "casual shoe",
                 "sneakers", "sneaker", "shoes", "shoe"],
    "sandals": ["sandals", "sandal", "slides", "slide", "floaters", "floater"],
    "t-shirts": ["t-shirts", "t-shirt", "t shirts", "t shirt", "tshirts",
                 "tshirt", "tees", "tee"],
    "shirts": ["shirts", "shirt"],
    "jeans": ["jeans", "denims", "denim"],
    "track pants": ["track pants", "trackpants", "track pant",
                    "joggers", "jogger"],
    "hoodies": ["hooded sweatshirt", "hooded sweatshirts", "hoodies",
                "hoodie", "sweatshirt", "sweatshirts"],
    "jackets": ["jackets", "jacket"],
    "dresses": ["dresses", "dress"],
    "kurtas": ["kurtas", "kurta"],
    "backpacks": ["backpacks", "backpack", "bag pack", "bag packs",
                  "bagpack", "rucksacks", "rucksack", "bag"],
    "caps": ["caps", "cap"],
    "headphones": ["headphones", "headphone", "headsets", "headset",
                   "earphones", "earphone"],
    "watches": ["wrist watch", "wristwatch", "wrist watches",
                "watches", "watch"],
    "wallets": ["wallets", "wallet"],
}

COLOURS = {
    "navy": ["navy blue", "navy"],
    "grey": ["grey", "gray"],
    "black": ["black", "kaala", "kala"],
    "white": ["white", "safed"],
    "pink": ["pink", "gulabi"],
    "red": ["red", "laal"],
    "blue": ["blue", "neela"],
    "green": ["green", "hara"],
    "yellow": ["yellow", "peela"],
    "brown": ["brown", "bhura"],
    "gold": ["gold", "golden"],
    "beige": ["beige"],
    "maroon": ["maroon"],
    "olive": ["olive green", "olive"],
    "silver": ["silver"],
    "tan": ["tan"],
}

BRANDS = ["Kesar Loom", "Audora", "Carrafel", "Horavo", "Kudova",
          "Ledgerly", "Loomsy", "Mehrin", "Northweft", "Pacevo",
          "Packwise", "Sonquil", "Strydo", "Tanaro", "Tikkra",
          "Urbanyx", "Wavlo", "Zentrail"]

# Categories whose products carry no size in the catalogue.
SIZELESS = {"backpacks", "caps", "headphones", "wallets", "watches"}

# Valid sizes per category family (from catalogue.csv).
SHOE_SIZES = {"6", "7", "8", "9", "10", "11"}
JEAN_SIZES = {"28", "30", "32", "34", "36"}
LETTER_SIZES = {"XS", "S", "M", "L", "XL", "XXL"}
LETTER_SIZES_NO_XXL = {"XS", "S", "M", "L", "XL"}

SIZE_WORDS = {"extra small": "XS", "extra large": "XL", "double xl": "XXL",
              "small": "S", "medium": "M", "large": "L"}

ONES = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
        "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
        "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
NUMBER_WORDS = set(ONES) | set(TENS) | {"hundred", "thousand", "and"}

HINDI_ONES = {"ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5,
              "chhah": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
              "gyarah": 11, "barah": 12, "terah": 13, "chaudrah": 14,
              "pandrah": 15, "solah": 16, "satrah": 17, "atharah": 18,
              "unnees": 19, "bees": 20, "tees": 30, "chalees": 40,
              "pachaas": 50}

FILTER_KEYS = ("category", "colour", "size", "brand", "max_price")

# Words that flag a correction is coming ("...oops, grey", "sorry, I meant
# size 7", "actually, make it Kudova", "no, change that to XL"). A commit is
# held while one of these is in the last few words: the corrected value has
# not arrived yet. ("no" is a correction marker in every dev request; "make"
# also introduces late constraints — either way, waiting is safe.)
CORRECTION_MARKERS = {"oops", "sorry", "actually", "wait", "meant", "mean",
                      "matlab", "rather", "change", "no", "make"}

_PRICE_TRIGGER = (r"(?:under|below|less than|not more than|up to|within"
                  r"|max(?:imum)?|budget(?: of)?)")
# Number words, longest first: the regex tries alternatives left to right,
# so "seventy" must come before "seven" or "under seventy five hundred"
# would match just "seven" (7, discarded) instead of 7500.
_NUMBER_WORDS_SORTED = sorted(NUMBER_WORDS, key=len, reverse=True)
_NUMBER_WORD_RE = r"(?:" + "|".join(_NUMBER_WORDS_SORTED) + r")"
_CATEGORY_PHRASES = sorted(
    {form for forms in CATEGORIES.values() for form in forms},
    key=len, reverse=True)
_CATEGORY_RE = r"(?:" + "|".join(re.escape(p) for p in _CATEGORY_PHRASES) + r")"
_SIZE_NUMBER_WORDS = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven)"
_HINDI_NUMBER_WORDS = "|".join(sorted(HINDI_ONES, key=len, reverse=True))


def _norm_text(words: list[str]) -> str:
    """Lowercase words, strip edge punctuation, split hyphens.

    A trailing "." after a letter becomes its own " ." token, so a price
    amount never swallows the next sentence's number word ("four thousand
    five hundred. one more thing" is 4500, not 4501). Decimals ("0.8k")
    and digit-ending periods ("1,500.") are unaffected.
    """
    cleaned = []
    for w in words:
        w = w.lower().replace("-", " ")
        # "Rs." is an abbreviation, not a sentence end — just strip it.
        if re.search(r"[a-z]\.$", w) and w[:-1] not in ("rs",):
            w = w[:-1] + " ."
        else:
            w = w.strip(".,!?;:\"'()[]")
        cleaned.append(w)
    return " ".join(cleaned).strip()


def _last_match(text: str, table: dict[str, list[str]]) -> str | None:
    """Last value mentioned: longest phrases first, spans consumed."""
    phrases = []
    for value, forms in table.items():
        for form in forms:
            phrases.append((len(form), form, value))
    phrases.sort(key=lambda p: -p[0])
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []
    for _, form, value in phrases:
        for m in re.finditer(rf"\b{re.escape(form)}\b", text):
            s, e = m.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            found.append((s, value))
    if not found:
        return None
    found.sort()
    return found[-1][1]


def _last_brand(text: str) -> str | None:
    phrases = sorted(BRANDS, key=len, reverse=True)
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []
    for brand in phrases:
        for m in re.finditer(rf"\b{re.escape(brand.lower())}\b", text):
            s, e = m.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            found.append((s, brand))
    if not found:
        return None
    found.sort()
    return found[-1][1]


def _parse_english_number(words: list[str]) -> int:
    """'forty five hundred' -> 4500; 'one thousand five hundred' -> 1500."""
    total = 0
    current = 0
    for w in words:
        if w in ONES:
            current += ONES[w]
        elif w in TENS:
            current += TENS[w]
        elif w == "hundred":
            current = (current or 1) * 100
        elif w == "thousand":
            total += (current or 1) * 1000
            current = 0
        elif w == "and":
            continue
        else:
            break
    return total + current


def _parse_hindi_number(base_word: str, mult_word: str, half: bool) -> int:
    base = HINDI_ONES[base_word] + (0.5 if half else 0.0)
    mult = 100 if mult_word == "sau" else 1000
    return int(base * mult)


def _last_price(text: str) -> int | None:
    """Last price expression in the text (corrections win)."""
    cands: list[tuple[int, int]] = []  # (end position, value)

    # "0.8k" / "1.5k" / "4k" — decimal-k shorthand.
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*k\b", text):
        cands.append((m.end(), int(float(m.group(1)) * 1000)))
    # "₹1,500" / "rs 7500".
    for m in re.finditer(r"(?:₹|rs\.?)\s*([\d,]+)", text):
        cands.append((m.end(), int(m.group(1).replace(",", ""))))
    # Trigger + digits: "under 2,500", "max 900 rupees", "budget 2,000".
    for m in re.finditer(
            _PRICE_TRIGGER + r"\s+(?:rs\.?\s*|₹)?([\d,]+(?:\.\d+)?)(?!\s*k\b)", text):
        cands.append((m.end(), int(float(m.group(1).replace(",", "")))))
    # Trigger + English number words: "under forty five hundred".
    for m in re.finditer(
            _PRICE_TRIGGER + r"\s+(" + _NUMBER_WORD_RE + r"(?:\s+"
            + _NUMBER_WORD_RE + r")*)", text):
        words = m.group(1).split()
        cands.append((m.end(), _parse_english_number(words)))
    # Hindi: "saadhe teen hazaar" (3500), "paanch hazaar" (5000),
    # "pandrah sau se kam" (1500).
    hindi_words = "|".join(sorted(HINDI_ONES, key=len, reverse=True))
    for m in re.finditer(
            r"(saadhe\s+)?(" + hindi_words + r")\s+(sau|hazaar)\b", text):
        cands.append((m.end(), _parse_hindi_number(
            m.group(2), m.group(3), bool(m.group(1)))))
    # "2000 tak" (up to 2000) / "1700 se kam" (less than 1700).
    for m in re.finditer(r"([\d,]+)\s+(?:tak|se\s+kam)\b", text):
        cands.append((m.end(), int(m.group(1).replace(",", ""))))
    # "dhai hazaar/sau" — dhai = two and a half (2500 / 250).
    for m in re.finditer(r"\bdhai\s+(sau|hazaar)\b", text):
        cands.append((m.end(), 2500 if m.group(1) == "hazaar" else 250))

    good = [(pos, v) for pos, v in cands if 100 <= v <= 50000]
    if not good:
        return None
    good.sort()
    return good[-1][1]


def _size_from_token(tok: str) -> str | None:
    tok = tok.strip().lower()
    if tok in SIZE_WORDS:
        return SIZE_WORDS[tok]
    if tok.upper() in LETTER_SIZES:
        return tok.upper()
    if tok in ONES:
        return str(ONES[tok])
    if tok in HINDI_ONES:
        return str(HINDI_ONES[tok])
    if tok.isdigit():
        return tok
    return None


def _last_size(text: str, category: str | None) -> str | None:
    """Last size mention (corrections win), validated against the category."""
    if category in ("running shoes", "sandals", "sneakers"):
        valid = SHOE_SIZES
    elif category == "jeans":
        valid = JEAN_SIZES
    elif category in ("dresses",):
        valid = LETTER_SIZES_NO_XXL
    elif category in ("hoodies", "jackets", "kurtas", "shirts",
                      "t-shirts", "track pants"):
        valid = LETTER_SIZES
    else:
        valid = None  # category unknown or sizeless: accept any size token

    cands: list[tuple[int, str]] = []  # (end position, size)
    size_tok = (r"(double\s+xl|extra\s+small|extra\s+large|one|two|three"
                r"|four|five|six|seven|eight|nine|ten|eleven"
                r"|xs|s|m|l|xl|xxl|\d+)")
    for m in re.finditer(r"(?:size|uk|waist)\s+" + size_tok + r"\b", text):
        v = _size_from_token(m.group(1))
        if v:
            cands.append((m.end(), v))
    for m in re.finditer(size_tok + r"\s+(?:size|uk|waist)\b", text):
        v = _size_from_token(m.group(1))
        if v:
            cands.append((m.end(), v))
    for m in re.finditer(r"\b(double\s+xl|extra\s+small|extra\s+large"
                         r"|small|medium|large|xs|xl|xxl)\b", text):
        v = _size_from_token(m.group(1))
        if v:
            cands.append((m.end(), v))
    # "2XL" / "2 XL" means XXL; "1XL" means XL.
    for m in re.finditer(r"\b([123])\s*xl\b", text):
        cands.append((m.end(), "XXL" if m.group(1) in ("2", "3") else "XL"))
    # Standalone letter sizes, matched as whole whitespace-delimited
    # tokens — never as a letter inside another word ("I'm" is not a size).
    for i, tok in enumerate(text.split()):
        if tok in ("s", "m", "l", "xs", "xl", "xxl"):
            cands.append((len(" ".join(text.split()[: i + 1])), tok.upper()))
    # A bare number word directly before a category phrase is a size
    # ("actually six slides" = size 6; "size seven floaters" is caught
    # above, but the bare form is not).
    for m in re.finditer(r"\b(" + _SIZE_NUMBER_WORDS + r")\s+(?:" +
                         _CATEGORY_RE + r")\b", text):
        cands.append((m.end(), _size_from_token(m.group(1))))
    # A number word (Hindi or English) + "number" is a size ("das number"
    # = size 10; "ten number" the same).
    for m in re.finditer(r"\b(?:" + _HINDI_NUMBER_WORDS + r"|"
                         r"one|two|three|four|five|six|seven|eight|nine|ten"
                         r"|eleven)\s+number\b", text):
        cands.append((m.end(), _size_from_token(m.group(0).split()[0])))
    if not cands:
        return None
    cands.sort()
    for _, v in reversed(cands):  # last mention first, keep the first valid
        if valid is None or v in valid:
            return v
    return None


def parse_filters(words: list[str]) -> dict:
    """Parse the words so far into the five official filter slots."""
    text = _norm_text(words)
    category = _last_match(text, CATEGORIES)
    colour = _last_match(text, COLOURS)
    brand = _last_brand(text)
    size = _last_size(text, category)
    max_price = _last_price(text)
    return {"category": category, "colour": colour, "size": size,
            "brand": brand, "max_price": max_price}


class Agent:
    """Sauda as a streaming agent (see the module docstring)."""

    def __init__(self, tools):
        self.tools = tools
        self.words: list[str] = []
        self.filters = {k: None for k in FILTER_KEYS}
        self.committed: str | None = None
        self.committed_filters: dict | None = None
        self.searched_filters: dict | None = None
        self.last_change_idx = 0
        self.last_hits: list | None = None

    def start(self, request_id):
        self.words = []
        self.filters = {k: None for k in FILTER_KEYS}
        self.committed = None
        self.committed_filters = None
        self.searched_filters = None
        self.last_change_idx = 0
        self.last_hits = None

    def _confidence(self) -> float:
        filled = sum(1 for k in FILTER_KEYS if self.filters[k] is not None)
        if self.filters["category"] in SIZELESS:
            filled += 1  # no size applies to this category
        return round(filled / 5, 2)

    def _commit_ready(self) -> bool:
        f = self.filters
        if not (f["category"] and f["colour"] and f["brand"]
                and f["max_price"]):
            return False
        if f["category"] in SIZELESS:
            return True
        return bool(f["size"])

    def _search_filters(self) -> dict:
        return {k: v for k, v in self.filters.items() if v is not None}

    def observe(self, word):
        self.words.append(word)
        new_filters = parse_filters(self.words)
        if new_filters != self.filters:
            self.filters = new_filters
            self.last_change_idx = len(self.words)
        out = {"filters": dict(self.filters),
               "confidence": self._confidence()}
        # Commit only once, and only when it is safe:
        #  * every applicable filter is stated,
        #  * the filters have been stable for 3 words (a correction that
        #    arrives right after the last filter lands is still to come),
        #  * no correction marker is in the last 4 words,
        #  * the filters changed since the last search (searches cost).
        # A wrong commit costs 1.0 and wipes out the earliness bonus; a
        # correct early commit gains at most 0.6 x the words left. One
        # wrong commit undoes ~11 correct early ones, so wait it out.
        if self.committed is None and self._commit_ready():
            stable = len(self.words) - self.last_change_idx >= 3
            recent = {w.lower().strip(".,!?;:\"'()")
                      for w in self.words[-4:]}
            marker = bool(recent & CORRECTION_MARKERS)
            if stable and not marker and self.filters != self.searched_filters:
                text = " ".join(self.words)
                hits = self.tools.search(text, self._search_filters(), k=2)
                self.searched_filters = dict(self.filters)
                self.last_hits = hits
                if len(hits) == 1:
                    self.committed = hits[0]["product_id"]
                    self.committed_filters = dict(self.filters)
                    out["commit"] = self.committed
        return out

    def finish(self):
        self.filters = parse_filters(self.words)
        if self.committed and self.filters == self.committed_filters:
            return self.committed
        text = " ".join(self.words)
        # Reuse the commit-check search when the filters have not changed
        # (and it found something — an empty result falls through to the
        # relaxation ladder below).
        if (self.last_hits and self.filters == self.searched_filters):
            return self.last_hits[0]["product_id"]
        filters = self._search_filters()
        hits = self.tools.search(text, filters, k=5)
        if hits:
            return hits[0]["product_id"]
        # Relax one filter at a time (cumulative), like the baseline.
        for drop in ("max_price", "size", "brand", "colour", "category"):
            filters.pop(drop, None)
            hits = self.tools.search(text, filters, k=5)
            if hits:
                return hits[0]["product_id"]
        return None
