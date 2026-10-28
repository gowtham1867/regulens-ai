import os
import shutil
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_VERCEL = bool(os.environ.get("VERCEL"))

# Compute paths for local vs Vercel Serverless environment
if IS_VERCEL:
    TMP_DIR = "/tmp"
    TMP_DB_PATH = os.path.join(TMP_DIR, "regulens.db")
    # Candidate source locations for seeded SQLite db
    src_candidates = [
        os.path.join(BASE_DIR, "regulens.db"),
        os.path.join(os.path.dirname(BASE_DIR), "regulens.db"),
        os.path.join(os.path.dirname(BASE_DIR), "backend", "regulens.db"),
    ]
    if not os.path.exists(TMP_DB_PATH):
        for candidate in src_candidates:
            if os.path.exists(candidate):
                try:
                    shutil.copy2(candidate, TMP_DB_PATH)
                    os.chmod(TMP_DB_PATH, 0o666)
                    break
                except Exception:
                    pass
    DEFAULT_DATABASE_URL = f"sqlite:///{TMP_DB_PATH}"
    DEFAULT_UPLOAD_DIR = os.path.join(TMP_DIR, "storage", "documents")
else:
    DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'regulens.db')}"
    DEFAULT_UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "documents")


class Settings(BaseSettings):
    PROJECT_NAME: str = "ReguLens AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "regulens-ai-secret-key-for-development-only-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    ALGORITHM: str = "HS256"

    DATABASE_URL: str = DEFAULT_DATABASE_URL
    UPLOAD_DIR: str = DEFAULT_UPLOAD_DIR
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15MB

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    REGULATORY_ACADEMIC_YEAR: str = "2025-2026"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure upload directory exists safely
try:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except Exception:
    pass
