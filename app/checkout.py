"""Simulated checkout.

The demo store has no real payment rails and no real inventory, so checkout
is explicitly SIMULATED: the order is created, a mock UPI payment is
recorded, and an order ID is returned. No real money moves, and every
surface that shows an order (UI, API, video) labels it SIMULATED.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass
class Order:
    order_id: str
    items: list
    total_inr: int
    payment_method: str
    status: str
    simulated: bool = True
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id, "items": self.items,
            "total_inr": self.total_inr, "payment_method": self.payment_method,
            "status": self.status, "simulated": self.simulated,
            "note": "SIMULATED order — no real money moved, no real shipment.",
        }


def create_order(items: list[dict], payment_method: str = "UPI (simulated)") -> Order:
    total = sum(int(i["price"]) * int(i.get("qty", 1)) for i in items)
    return Order(
        order_id=f"SAU-{random.randint(100000, 999999)}",
        items=items,
        total_inr=total,
        payment_method=payment_method,
        status="confirmed",
        created_at=time.time(),
    )
