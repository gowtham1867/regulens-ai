import sys, os
print("Step 1: start", flush=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print("Step 2: sys.path ready", flush=True)
import asyncio
print("Step 3: asyncio ready", flush=True)
import httpx
print("Step 4: httpx ready", flush=True)
from app.config import settings
print("Step 5: config ready", flush=True)
from app.database import Base, engine
print("Step 6: database ready", flush=True)
from app.api.v1 import api_router
print("Step 7: router ready", flush=True)
from app.main import app
print("Step 8: app ready", flush=True)

