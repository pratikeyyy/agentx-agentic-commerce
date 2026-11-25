# Sauda — Anticipatory Shopping Agent

**Techfest 2026 · AgentX · Challenge 1: Anticipatory Commerce**
**Entrant:** Pratik Kumar (individual), B.Tech CSE (AI), ABESIT, Ghaziabad

Sauda is an AI shopping agent that understands incomplete requests and anticipates
the preferences shoppers never state — then recommends, compares and checks out.
Built with Python + FastAPI; the UI is a single-page chat app that shows the
agent's full reasoning trace.

## What it does

A shopper types an incomplete request — `"gift for mom under 2000"`,
`"phone for mom, easy to use"`, `"cheapest laptop for college"` — and Sauda:

1. **Understands** — parses category, budget, recipient, occasion, attributes,
   use case (rule-based intent parser, `app/intent.py`).
2. **Anticipates** — infers the unstated preferences: a gift for mom implies
   comfort, simplicity and durability; gaming implies performance and a real
   GPU; "cheapest" makes price decisive (`app/preferences.py`). Every
   inference is shown to the user with its reason.
3. **Discovers** — finds in-stock products through the Rezolve Labs adapter
   (`app/rezolve.py`: brainpowa intent + Rezolve Commerce discovery).
4. **Ranks** — transparent weighted score: text relevance 30, attribute fit 25,
   value 20, budget fit 15, preference fit 10 (`app/ranking.py`).
5. **Governs** — policy check via the Agentic Plug-in (in stock, in budget,
   no banned substitution).
6. **Recommends** — top 3 with reasons + a side-by-side comparison.
7. **Checks out** — simulated order (no real money moves, labelled everywhere).

### The honest-budget rule

A budget the shopper **stated** is a hard filter — the top pick is never over
budget when an in-budget option exists. A budget Sauda **guessed** is only a
soft prior, and its weight scales with how precisely the shopper named the
product: `"apple watch"` still finds the Apple Watch at ₹29,900 despite a
typical wearables budget of ₹2,500, while `"phone for mom, easy to use"` does
not jump to a ₹52,999 iPhone when a ₹14,499 Samsung fits. This rule alone
lifted top-1 accuracy from 28% to 100% on the development set.

## Measured results (40-request development set)

| Metric | Result |
|---|---|
| Category accuracy | 97.4% |
| Budget compliance (top pick in stated budget) | 100% |
| Top-1 accuracy | **100%** |
| Top-3 hit rate | **100%** |
| Average latency | 5 ms |
| Max latency | 23 ms |

Reproduce: `python3 eval/run_eval.py` (writes `eval/outputs/metrics.json`).

## Run it

```bash
python3 -m venv venv && ./venv/bin/pip install fastapi uvicorn
./venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

API: `GET /api/health` · `POST /api/chat {"message": "..."}` ·
`POST /api/checkout {"product_id": "P051", "qty": 1}` · `GET /api/products`.

Demo scenes (for the video): `/?demo=1&scene=N&q=...` — scene 1 landing,
2 trace, 3 recommendations, 4 comparison, 5 checkout.

## Tests

```bash
./venv/bin/pip install pytest
./venv/bin/python -m pytest tests/ -q
```

## What is live vs simulated — read this first

- **Catalog:** 100 representative Indian-market products across 8 categories
  (`data/products.json`) — a simulated demo catalog, labelled as such.
- **Rezolve Labs:** the integration is fully implemented (`app/rezolve.py`,
  `docs/REZOLVE_INTEGRATION.md`) against a Rezolve-compatible stub that runs
  the identical code path. Rezolve Labs is invite-only; the competition coupon
  is shared with registered AgentX participants after Techfest registration.
  Set `REZOLVE_API_KEY` + `REZOLVE_BASE_URL` to switch to live mode — no code
  change needed. Every trace entry records its source (`rezolve:stub` or
  `rezolve:live`); nothing pretends a live call happened when it did not.
- **Checkout:** simulated end to end. Orders get an `SAU-` number, no money
  moves, no shipment is created. Labelled "SIMULATED" in the API response
  and the UI.

## Files

```
app/            intent, preferences, ranking, rezolve adapter, agent, checkout, API
data/           products.json (100 demo products), devset.json (40 eval requests)
eval/           run_eval.py + outputs/metrics.json
static/         index.html — chat UI with trace, comparison, checkout
docs/           ABSTRACT.md (498 words), REZOLVE_INTEGRATION.md
tests/          test_agent.py
demo/           sauda-demo.mp4 (3-minute demo video)
```

## Licence

MIT. Demo catalog prices/products are representative examples, not live listings.
