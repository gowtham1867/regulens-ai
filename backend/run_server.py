import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn

if __name__ == "__main__":
    print(">>> Starting ReguLens AI Uvicorn Server on http://127.0.0.1:8000...", flush=True)
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        print(f">>> CRITICAL ERROR starting uvicorn: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

