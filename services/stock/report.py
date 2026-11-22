import os, sys
from datetime import datetime
import httpx

AUTH_URL = os.environ.get("AUTH_URL", "http://auth:8000")
STOCK_URL = os.environ.get("STOCK_URL", "http://stock:8000")

token = httpx.post(f"{AUTH_URL}/api/auth/login", json={
    "username": os.environ["ADMIN_USERNAME"], "password": os.environ["ADMIN_PASSWORD"]}, timeout=10)
token.raise_for_status()
headers = {"Authorization": f"Bearer {token.json()['access_token']}"}

items = httpx.get(f"{STOCK_URL}/api/stock/low", headers=headers, timeout=10).json()
print(f"=== Low stock report - {datetime.now():%Y-%m-%d %H:%M} ===")
if not items:
    print("All products are above their thresholds.")
for i in items:
    print(f"[LOW] {i['sku']:<10} {i['name']:<25} qty={i['quantity']:<5} threshold={i['low_stock_threshold']} supplier={i['supplier']}")
sys.exit(0)
