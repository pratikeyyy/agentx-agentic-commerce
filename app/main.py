"""Sauda — Anticipatory Shopping Agent. FastAPI service + demo UI.

Run:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Then open http://127.0.0.1:8000

Demo scenes (for screenshots / the demo video):
    /?demo=1&scene=1&q=gift%20for%20mom%20under%202000
    scene=1  landing + typed query
    scene=2  agent trace (understand/anticipate/discover/rank)
    scene=3  recommendations + reasons
    scene=4  comparison table
    scene=5  checkout (simulated)
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import SaudaAgent
from .catalog import Catalog
from .checkout import create_order

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Sauda — Anticipatory Shopping Agent",
              description="Techfest AgentX 2026 · Challenge 1: Anticipatory Commerce")
agent = SaudaAgent(Catalog())

app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")


class ChatRequest(BaseModel):
    message: str


class CheckoutRequest(BaseModel):
    product_id: str
    qty: int = 1


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE, "static", "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "agent": "sauda", "rezolve_source": agent.rezolve.source,
            "products": len(agent.catalog.products)}


@app.post("/api/chat")
def chat(req: ChatRequest):
    return JSONResponse(agent.run(req.message).to_dict())


@app.post("/api/checkout")
def checkout(req: CheckoutRequest):
    product = agent.catalog.get(req.product_id)
    if product is None:
        return JSONResponse({"error": "unknown product"}, status_code=404)
    order = create_order([{"id": product.id, "name": product.name,
                           "price": product.price, "qty": req.qty}])
    return JSONResponse(order.to_dict())


@app.get("/api/products")
def products(q: str = "", category: str = ""):
    items = agent.catalog.search(q) if q else agent.catalog.products
    if category:
        items = [p for p in items if p.category == category]
    return JSONResponse([p.to_dict() for p in items[:30]])
