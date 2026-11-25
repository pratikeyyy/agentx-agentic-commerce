# Rezolve Labs integration

## What Rezolve Labs is

Per Rezolve Ai's public material (Nov 2026), the Brain Commerce platform offers:

| Capability | What it does |
|---|---|
| **brainpowa** | Commerce-trained intent models that interpret what a shopper really wants. |
| **Rezolve Commerce** | Agent-ready product discovery — trusted answers from a merchant's own catalog, with live pricing and availability. |
| **Brain Checkout** | Agentic checkout that converts intent into a sale. |
| **Rezolve Pay** | Payment optimisation for the transaction. |
| **Agentic Plug-in** | Governance — what an agent may say, which products it may recommend, how substitutions, pricing and fulfilment are handled. |
| **TraceWare** | Traceability of agentic transactions. |

Sauda uses four of these: **brainpowa** (intent interpretation),
**Rezolve Commerce** (discovery), **Brain Checkout** (purchase flow) and the
**Agentic Plug-in** (governance policy check).

## How the integration is implemented

`app/rezolve.py` — `RezolveClient` exposes exactly those capabilities:

```python
client.interpret_intent(text)   # brainpowa
client.discover(profile, query) # Rezolve Commerce
client.checkout(items)          # Brain Checkout
client.govern(recommendations)  # Agentic Plug-in
```

Every method returns a `RezolveResult` with a `source` field:
`"rezolve:stub"` or `"rezolve:live"`. The agent's 7-step trace records that
source on every step, so the UI and the API always show which calls were
live and which were stubbed.

## Live vs stub — the honest part

Rezolve Labs is **invite-only**: sign-in is by Microsoft or an email magic
link, and "access is by invitation — use the email address your invite was
sent to". For AgentX, the coupon and API access are shared with **registered
participants** after Techfest registration. No public API documentation was
available at build time.

So this repository ships the integration in **stub mode by default**:

- The stub implements the same four methods against the local demo catalog
  (`data/products.json`), through the identical code path the live client
  uses — same request shapes, same result shapes, same trace sources.
- Switching to live mode is one environment change, no code change:

```bash
export REZOLVE_API_KEY="<coupon key from Techfest registration>"
export REZOLVE_BASE_URL="https://api.rezolvelabs.com/v1"   # as given to participants
```

- When `REZOLVE_API_KEY` is set, `RezolveClient.live` becomes true, the
  source flips to `rezolve:live`, and the adapter calls the real endpoints
  (`brainpowa/interpret`, `commerce/discover`, `checkout/create`,
  `plugin/govern`). If a live call fails, the agent falls back to the stub
  for that step and records the fallback in the trace — it never fails a
  shopper's request silently, and never claims a live result it did not get.

**Nothing in this entry pretends a live Rezolve call happened when it did
not.** The demo video, the UI and the API all show `rezolve:stub` until a
real key is present. The abstract says the same thing in plain language.

## What to do after registration (for the parent agent / user)

1. Register the team on the Techfest AgentX portal — this is what releases
   the Rezolve coupon and the official public development set.
2. Create the Rezolve Labs account with the invited email, redeem the coupon.
3. Set `REZOLVE_API_KEY` / `REZOLVE_BASE_URL`, re-run
   `python3 eval/run_eval.py` and the demo, and confirm the trace shows
   `rezolve:live`.
4. Re-run the agent on the official public development set when it arrives
   and update `eval/outputs/metrics.json`.
