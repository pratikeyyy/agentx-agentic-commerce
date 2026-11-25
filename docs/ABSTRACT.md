# Sauda — an anticipatory shopping agent

**Techfest 2026 · AgentX · Challenge 1: Anticipatory Commerce**
**Entrant:** Pratik Kumar (individual), B.Tech CSE (AI), ABESIT, Ghaziabad
**Repository:** https://github.com/pratikeyyy/agentx-agentic-commerce
**Demo video:** see the repository (`demo/sauda-demo.mp4`)

Most online shoppers do not state what they actually want. They type "gift for mom under 2000" or "phone for mom, easy to use" — incomplete requests where the real constraints (who it is for, what matters, what a fair budget is) are left unsaid. Sauda is an anticipatory commerce agent that fills in those gaps before it recommends anything, instead of interrogating the shopper or dumping a keyword-matched list.

Sauda works in seven steps. First it parses the request: category, budget, recipient, occasion, attributes and use case. Then — the core of the entry — it infers the preferences the shopper did not state: a gift for mom implies comfort, simplicity and durability; a gaming laptop implies performance and a real GPU; a request for the cheapest laptop makes price decisive. These inferences are shown with reasons, never hidden. It then discovers products through Rezolve Labs, ranks them with a transparent weighted score (text relevance 30, attribute fit 25, value 20, budget fit 15, preference fit 10), applies a governance policy check, recommends the top three with reasons and a comparison, then checks out.

Two rules make the ranking honest. A budget the shopper stated is a hard filter: the top pick is never over budget when an in-budget option exists. A budget Sauda guessed is only a soft prior — and its weight scales with how precisely the shopper named the product. So "apple watch" still finds the Apple Watch at ₹29,900 despite a typical wearables budget of ₹2,500, while "phone for mom, easy to use" does not jump to a ₹52,999 iPhone when a ₹14,499 Samsung fits. This rule alone lifted top-1 accuracy from 28% to 100% on our 40-request set.

Integration with Rezolve Labs uses four capabilities: brainpowa for intent interpretation, Rezolve Commerce for agent-ready product discovery with live price and availability, Brain Checkout for the purchase flow, and the Agentic Plug-in for governance. Rezolve Labs access is by invitation, with the competition coupon shared after registration; this entry therefore ships with the integration fully implemented against a Rezolve-compatible stub that runs the identical code path, and the live API key is a drop-in swap via environment variables. Every trace entry records its source ("rezolve:stub" or "rezolve:live"), so nothing in the demo pretends a live Rezolve call happened when it did not.

The demo catalog holds 100 representative Indian-market products across eight categories with realistic prices, ratings and stock, labelled as simulated. Checkout is simulated end to end — no real money moves and no real shipment is created — and is labelled as such everywhere it appears.

Measured on our 40-request development set (each request with a category, a budget verdict and a ground-truth best pick): category accuracy 97.4%, budget compliance 100%, top-1 accuracy 100%, top-3 hit rate 100%, average latency 5 ms. The agent is a Python/FastAPI service with a single-page chat UI that exposes the full reasoning trace; the code, catalog, evaluation harness and demo video are in the linked repository.
