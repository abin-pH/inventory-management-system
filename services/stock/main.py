import os, time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, DateTime, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
PRODUCTS_URL = os.environ.get("PRODUCTS_URL", "http://products:8000")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


class StockLevel(Base):
    __tablename__ = "stock_levels"
    product_id: Mapped[int] = mapped_column(primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)


class Transaction(Base):
    __tablename__ = "stock_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(3))  # "in" or "out"
    quantity: Mapped[int] = mapped_column(Integer)
    username: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


@asynccontextmanager
async def lifespan(app):
    for _ in range(30):
        try:
            Base.metadata.create_all(engine)
            break
        except Exception:
            time.sleep(2)
    yield


app = FastAPI(title="Stock Service", lifespan=lifespan)


class Move(BaseModel):
    product_id: int
    type: Literal["in", "out"]
    quantity: int = Field(gt=0)


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    payload["_auth"] = authorization  # forwarded to the products service
    return payload


def fetch_products(user, pid: int | None = None):
    url = f"{PRODUCTS_URL}/api/products" + (f"/{pid}" if pid else "")
    try:
        r = httpx.get(url, headers={"Authorization": user["_auth"]}, timeout=5)
    except httpx.HTTPError:
        raise HTTPException(503, "Products service unavailable")
    if r.status_code == 404:
        raise HTTPException(404, "Product not found")
    r.raise_for_status()
    return r.json()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/stock/move", status_code=201)
def move_stock(m: Move, user=Depends(current_user)):
    fetch_products(user, m.product_id)  # makes sure the product exists
    with Session() as s:
        level = s.scalar(select(StockLevel).where(StockLevel.product_id == m.product_id).with_for_update())
        if not level:
            level = StockLevel(product_id=m.product_id, quantity=0)
            s.add(level)
        if m.type == "out" and level.quantity < m.quantity:
            raise HTTPException(400, f"Only {level.quantity} in stock")
        level.quantity += m.quantity if m.type == "in" else -m.quantity
        s.add(Transaction(product_id=m.product_id, type=m.type, quantity=m.quantity,
                          username=user["sub"], created_at=datetime.now(timezone.utc)))
        s.commit()
        return {"product_id": m.product_id, "quantity": level.quantity}


@app.get("/api/stock/levels")
def levels(user=Depends(current_user)):
    with Session() as s:
        return [{"product_id": l.product_id, "quantity": l.quantity} for l in s.scalars(select(StockLevel))]


@app.get("/api/stock/low")
def low_stock(user=Depends(current_user)):
    products = fetch_products(user)
    with Session() as s:
        qty = {l.product_id: l.quantity for l in s.scalars(select(StockLevel))}
    return [{**p, "quantity": qty.get(p["id"], 0)} for p in products
            if qty.get(p["id"], 0) <= p["low_stock_threshold"]]


@app.get("/api/stock/transactions")
def transactions(limit: int = 50, user=Depends(current_user)):
    with Session() as s:
        rows = s.scalars(select(Transaction).order_by(Transaction.id.desc()).limit(limit))
        return [{"id": t.id, "product_id": t.product_id, "type": t.type, "quantity": t.quantity,
                 "username": t.username, "created_at": t.created_at.isoformat()} for t in rows]
