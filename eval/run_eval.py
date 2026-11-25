"""Run Sauda over the development set and write benchmark outputs.

Metrics:
  * category accuracy  — inferred category == expected category
  * budget compliance  — primary pick price <= stated budget (when stated)
  * top-1 accuracy    — primary pick == expected product
  * top-3 hit rate    — expected product in the top 3
  * avg latency (ms)
D30 ("something for my room") has no ground truth: it checks that the
agent asks its one clarifying question and still returns 3 recommendations.

Outputs: eval/outputs/devset_outputs.json (per-request results) and
eval/outputs/metrics.json (aggregate). Both go into the Round 1 Drive folder.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent import SaudaAgent
from app.catalog import Catalog

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _check_must(primary: dict, must: list) -> list[str]:
    """Return the list of must-have constraints the primary pick violates."""
    failed = []
    if not primary:
        return ["no recommendation"]
    p = primary["product"]
    for rule in must:
        if rule.startswith("price<="):
            if p["price"] > int(rule.split("<=")[1]):
                failed.append(rule)
        elif rule.startswith("camera_mp>="):
            if p["attrs"].get("camera_mp", 0) < int(rule.split(">=")[1]):
                failed.append(rule)
        elif rule.startswith("battery_mah>="):
            if p["attrs"].get("battery_mah", 0) < int(rule.split(">=")[1]):
                failed.append(rule)
        elif rule.startswith("battery_h>="):
            if p["attrs"].get("battery_h", 0) < int(rule.split(">=")[1]):
                failed.append(rule)
        elif rule.startswith("ram_gb>="):
            if p["attrs"].get("ram_gb", 0) < int(rule.split(">=")[1]):
                failed.append(rule)
        elif rule.startswith("weight_g<="):
            if p["attrs"].get("weight_g", 10**9) > int(rule.split("<=")[1]):
                failed.append(rule)
        elif rule.startswith("capacity_l>="):
            if p["attrs"].get("capacity_l", 0) < float(rule.split(">=")[1]):
                failed.append(rule)
        elif rule.startswith("brand="):
            if p["brand"].lower() != rule.split("=")[1].lower():
                failed.append(rule)
        elif rule == "5g":
            if not p["attrs"].get("5g"):
                failed.append(rule)
        elif rule == "anc=true":
            if not p["attrs"].get("anc"):
                failed.append(rule)
        elif rule == "gps=true":
            if not p["attrs"].get("gps"):
                failed.append(rule)
    return failed


def main() -> None:
    with open(os.path.join(BASE, "data", "devset.json"), encoding="utf-8") as f:
        devset = json.load(f)["requests"]
    agent = SaudaAgent(Catalog())
    results = []
    n_scored = n_cat = n_budget = n_top1 = n_top3 = 0
    latencies = []
    for item in devset:
        run = agent.run(item["request"])
        primary = run.primary
        rec_ids = [r["product"]["id"] for r in run.recommendations]
        row = {
            "id": item["id"], "request": item["request"],
            "expected_category": item["expected_category"],
            "inferred_category": run.intent.category,
            "expected_product": item["expected_product"],
            "primary": primary["product"]["id"] if primary else None,
            "top3": rec_ids,
            "latency_ms": round(run.total_ms, 1),
            "clarifying_question": run.clarifying_question,
        }
        latencies.append(run.total_ms)
        if item["expected_category"] is None:
            # Ambiguous request: success = asks one question AND still recommends.
            row["ambiguous_ok"] = bool(run.clarifying_question) and len(rec_ids) == 3
            results.append(row)
            continue
        n_scored += 1
        cat_ok = run.intent.category == item["expected_category"]
        budget_ok = (item["expected_budget"] is None or not primary
                     or primary["product"]["price"] <= item["expected_budget"])
        top1 = primary and primary["product"]["id"] == item["expected_product"]
        top3 = item["expected_product"] in rec_ids
        must_failed = _check_must(primary, item["must"])
        row.update({
            "category_ok": cat_ok, "budget_ok": budget_ok,
            "top1": bool(top1), "top3": bool(top3),
            "must_failed": must_failed,
        })
        n_cat += cat_ok
        n_budget += budget_ok
        n_top1 += top1
        n_top3 += top3
        results.append(row)

    metrics = {
        "n_requests": len(devset),
        "n_scored": n_scored,
        "category_accuracy": round(n_cat / n_scored, 3) if n_scored else None,
        "budget_compliance": round(n_budget / n_scored, 3) if n_scored else None,
        "top1_accuracy": round(n_top1 / n_scored, 3) if n_scored else None,
        "top3_hit_rate": round(n_top3 / n_scored, 3) if n_scored else None,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "max_latency_ms": round(max(latencies), 1) if latencies else None,
    }
    out_dir = os.path.join(BASE, "eval", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "devset_outputs.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))
    fails = [r for r in results if r.get("top1") is False]
    print(f"\ntop-1 misses ({len(fails)}):")
    for r in fails:
        print(f"  {r['id']}: '{r['request']}' -> got {r['primary']}, expected {r['expected_product']}")


if __name__ == "__main__":
    main()
