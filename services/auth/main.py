import os, time, hashlib, secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="staff")


def hash_pw(pw: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"


def verify_pw(pw: str, stored: str) -> bool:
    salt, _ = stored.split("$")
    return secrets.compare_digest(hash_pw(pw, salt), stored)


def init_db():
    for _ in range(30):  # wait for Postgres to be ready
        try:
            Base.metadata.create_all(engine)
            break
        except Exception:
            time.sleep(2)
    with Session() as s:
        admin = os.environ.get("ADMIN_USERNAME", "admin")
        if not s.scalar(select(User).where(User.username == admin)):
            s.add(User(username=admin, role="admin",
                       password_hash=hash_pw(os.environ.get("ADMIN_PASSWORD", "admin123"))))
            s.commit()


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="Auth Service", lifespan=lifespan)


class Credentials(BaseModel):
    username: str
    password: str
    role: str = "staff"


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(c: Credentials):
    with Session() as s:
        u = s.scalar(select(User).where(User.username == c.username))
        if not u or not verify_pw(c.password, u.password_hash):
            raise HTTPException(401, "Wrong username or password")
        exp = datetime.now(timezone.utc) + timedelta(hours=8)
        token = jwt.encode({"sub": u.username, "role": u.role, "exp": exp}, JWT_SECRET, algorithm="HS256")
        return {"access_token": token, "role": u.role}


@app.post("/api/auth/register", status_code=201)
def register(c: Credentials, user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    with Session() as s:
        if s.scalar(select(User).where(User.username == c.username)):
            raise HTTPException(409, "Username taken")
        s.add(User(username=c.username, password_hash=hash_pw(c.password),
                   role=c.role if c.role in ("admin", "staff") else "staff"))
        s.commit()
    return {"created": c.username}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return {"username": user["sub"], "role": user["role"]}
