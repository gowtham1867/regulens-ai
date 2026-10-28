import sys
import os

# Ensure backend root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

for directory in (BACKEND_DIR, ROOT_DIR):
    if directory not in sys.path:
        sys.path.insert(0, directory)

from app.main import app

