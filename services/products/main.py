import os, time
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Float, Integer, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    supplier: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[float] = mapped_column(Float, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


@asynccontextmanager
async def lifespan(app):
    for _ in range(30):
        try:
            Base.metadata.create_all(engine)
            break
        except Exception:
            time.sleep(2)
    yield


app = FastAPI(title="Products Service", lifespan=lifespan)


class ProductIn(BaseModel):
    sku: str
    name: str
    supplier: str = ""
    price: float = Field(0, ge=0)
    low_stock_threshold: int = Field(10, ge=0)


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")


def admin_only(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    return user


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/products")
def list_products(user=Depends(current_user)):
    with Session() as s:
        return [p.to_dict() for p in s.scalars(select(Product).order_by(Product.id))]


@app.get("/api/products/{pid}")
def get_product(pid: int, user=Depends(current_user)):
    with Session() as s:
        p = s.get(Product, pid)
        if not p:
            raise HTTPException(404, "Product not found")
        return p.to_dict()


@app.post("/api/products", status_code=201)
def create_product(data: ProductIn, user=Depends(admin_only)):
    with Session() as s:
        p = Product(**data.model_dump())
        s.add(p)
        try:
            s.commit()
        except IntegrityError:
            raise HTTPException(409, "SKU already exists")
        return p.to_dict()


@app.put("/api/products/{pid}")
def update_product(pid: int, data: ProductIn, user=Depends(admin_only)):
    with Session() as s:
        p = s.get(Product, pid)
        if not p:
            raise HTTPException(404, "Product not found")
        for k, v in data.model_dump().items():
            setattr(p, k, v)
        s.commit()
        return p.to_dict()


@app.delete("/api/products/{pid}", status_code=204)
def delete_product(pid: int, user=Depends(admin_only)):
    with Session() as s:
        p = s.get(Product, pid)
        if not p:
            raise HTTPException(404, "Product not found")
        s.delete(p)
        s.commit()
