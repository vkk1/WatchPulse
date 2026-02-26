from pathlib import Path
import os

from dotenv import load_dotenv


def _load_env() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    repo_root = backend_dir.parent
    load_dotenv(repo_root / ".env")
    load_dotenv(backend_dir / ".env")


_load_env()


class Settings:
    app_name: str = "WatchPulse API"
    app_version: str = "0.1.0"
    rolex_brand: str = "rolex"
    supabase_url: str = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    supabase_key: str = os.getenv("SUPABASE_KEY", "").strip().strip('"').strip("'")


settings = Settings()
