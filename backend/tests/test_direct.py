import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.main import app


async def test_asgi():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/health",
        "raw_path": b"/api/health",
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "http_version": "1.1",
    }
    
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}
        
    async def send(message):
        print("ASGI Response Message:", message)

    await app(scope, receive, send)

if __name__ == "__main__":
    asyncio.run(test_asgi())

