"""Tests for Sauda — the AgentX anticipatory shopping agent.

Run:  python -m pytest tests/ -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import SaudaAgent
from app.catalog import Catalog
from app.checkout import create_order
from app.intent import parse_intent
from app.preferences import infer_preferences
from app.ranking import rank
from app.rezolve import RezolveClient

CATALOG = Catalog()
AGENT = SaudaAgent(CATALOG)


def test_catalog_has_100_products_in_8_categories():
    assert len(CATALOG.products) == 100
    assert len(CATALOG.categories()) == 8


def test_intent_parses_budget_recipient_and_category():
    intent = parse_intent("gift for mom under 2000")
    assert intent.budget == 2000
    assert intent.budget_explicit is True
    assert intent.recipient == "mom"
    assert intent.is_gift is True


def test_intent_budget_is_explicit_only_when_stated():
    assert parse_intent("apple watch").budget_explicit is False
    assert parse_intent("phone under 15000").budget_explicit is True


def test_preferences_infer_mom_gift_signals():
    profile = infer_preferences(parse_intent("gift for mom under 2000"))
    assert profile.prefs.get("comfort", 0) > 0
    assert profile.prefs.get("womenswear", 0) > 0


def test_gift_for_mom_under_2000_recommends_in_budget_saree():
    run = AGENT.run("gift for mom under 2000")
    assert run.primary["product"]["id"] == "P051"
    assert run.primary["product"]["price"] <= 2000
    assert len(run.recommendations) == 3


def test_phone_under_15000_good_camera_recommends_m34():
    run = AGENT.run("phone under 15000, good camera")
    assert run.primary["product"]["id"] == "P002"
    assert run.primary["product"]["price"] <= 15000


def test_apple_watch_finds_apple_watch_despite_assumed_budget():
    # The shopper named the product: the guessed wearables budget must not veto it.
    run = AGENT.run("apple watch")
    assert run.primary["product"]["id"] == "P036"


def test_phone_for_mom_does_not_jump_to_iphone():
    # Vague request: the guessed phone budget must hold.
    run = AGENT.run("phone for mom, easy to use")
    assert run.primary["product"]["id"] == "P002"
    assert run.primary["product"]["price"] <= 20000


def test_cheapest_laptop_is_the_cheapest():
    run = AGENT.run("cheapest laptop for college")
    assert run.primary["product"]["id"] == "P015"


def test_stated_budget_is_a_hard_filter():
    # No top pick may exceed a stated budget when an in-budget option exists.
    for q, budget in [("phone under 15000", 15000),
                      ("laptop under 50000 for coding", 50000),
                      ("gift for mom under 2000", 2000)]:
        run = AGENT.run(q)
        assert run.primary["product"]["price"] <= budget, q


def test_trace_has_all_steps_and_sources():
    run = AGENT.run("gift for mom under 2000")
    steps = [t.step for t in run.trace]
    assert steps == ["understand", "anticipate", "discover", "rank", "govern"]
    assert all(t.source for t in run.trace)
    assert run.total_ms < 1000


def test_rezolve_adapter_defaults_to_stub_and_records_source():
    client = RezolveClient(CATALOG)
    assert client.live is False
    assert client.source == "rezolve:stub"
    res = client.interpret_intent("gift for mom under 2000")
    assert res.source == "rezolve:stub"


def test_checkout_is_simulated_and_labelled():
    order = create_order([{"id": "P051", "name": "Libas Saree",
                           "price": 1499, "qty": 1}])
    d = order.to_dict()
    assert d["simulated"] is True
    assert d["status"] == "confirmed"
    assert d["total_inr"] == 1499
    assert d["order_id"].startswith("SAU-")
    assert "SIMULATED" in d["note"]


def test_vague_query_asks_a_clarifying_question_but_still_recommends():
    # D30: no category can be inferred — the agent asks one clarifying
    # question and still returns a best-guess top 3.
    run = AGENT.run("something for my room")
    assert run.clarifying_question is not None
    assert len(run.recommendations) == 3
    assert run.primary is not None


def test_devset_top1_is_perfect():
    devset = json.load(open("data/devset.json"))
    scored = [i for i in devset["requests"] if i.get("expected_product")]
    correct = 0
    for item in scored:
        run = AGENT.run(item["request"])
        if run.primary and run.primary["product"]["id"] == item["expected_product"]:
            correct += 1
    assert correct == len(scored), f"top-1 {correct}/{len(scored)}"
