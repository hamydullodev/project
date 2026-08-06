import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.graph import run_agent
from app.config import API_HOST, API_PORT
from app.database.db import (
    add_favorite,
    add_price_alert,
    get_recent_searches,
    init_db,
    list_favorites,
    list_price_alerts,
    remove_favorite,
)

app = FastAPI(title="AI Pharmacy Price Comparison Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    tool_calls: list[dict]
    tool_results: list[dict]


class FavoriteRequest(BaseModel):
    name: str
    store: str
    price: float | None = None
    currency: str = "UZS"
    url: str | None = None


class PriceAlertRequest(BaseModel):
    query: str
    target_price: float


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    result = run_agent(thread_id, req.message)
    return ChatResponse(thread_id=thread_id, **result)


@app.get("/recent-searches")
def recent_searches(limit: int = 10):
    return get_recent_searches(limit)


@app.get("/favorites")
def get_favorites():
    return list_favorites()


@app.post("/favorites")
def post_favorite(req: FavoriteRequest):
    add_favorite(req.model_dump())
    return {"status": "ok"}


@app.delete("/favorites/{favorite_id}")
def delete_favorite(favorite_id: int):
    remove_favorite(favorite_id)
    return {"status": "ok"}


@app.get("/price-alerts")
def get_price_alerts():
    return list_price_alerts()


@app.post("/price-alerts")
def post_price_alert(req: PriceAlertRequest):
    add_price_alert(req.query, req.target_price)
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=False)
