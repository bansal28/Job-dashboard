"""
Central settings for backend services.

Values come from environment variables first, then fall back to scrapers/config.py
where this repo historically stores local secrets.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
TEMPLATES_DIR = ROOT_DIR / "templates"
SCRAPERS_DIR = ROOT_DIR / "scrapers"

if str(SCRAPERS_DIR) not in sys.path:
    sys.path.append(str(SCRAPERS_DIR))


def _scraper_config_value(name: str, default: str = "") -> str:
    try:
        import config as scraper_config  # type: ignore
    except Exception:
        return default
    return getattr(scraper_config, name, default)


def get_setting(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is not None:
        return value
    return _scraper_config_value(name, default)


GROQ_API_KEY = get_setting("GROQ_API_KEY", "")
GROQ_MODEL = get_setting("GROQ_MODEL", "llama-3.3-70b-versatile")
JUDGE_MODEL = get_setting("JUDGE_MODEL", GROQ_MODEL)

EMBEDDING_MODEL = get_setting("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_FALLBACK_MODEL = get_setting("EMBEDDING_FALLBACK_MODEL", "all-MiniLM-L6-v2")
VECTOR_STORE_PATH = Path(get_setting("VECTOR_STORE_PATH", str(DATA_DIR / "chroma")))
VECTOR_COLLECTION = get_setting("VECTOR_COLLECTION", "resume_chunks")

RETRIEVAL_K = int(get_setting("RETRIEVAL_K", "6") or "6")
RETRIEVAL_METHOD = get_setting("RETRIEVAL_METHOD", "hybrid")
RRF_K = int(get_setting("RRF_K", "60") or "60")
RRF_DENSE_WEIGHT = float(get_setting("RRF_DENSE_WEIGHT", "1.0") or "1.0")
RRF_SPARSE_WEIGHT = float(get_setting("RRF_SPARSE_WEIGHT", "1.0") or "1.0")

RESUME_PATH = Path(get_setting("RESUME_PATH", str(TEMPLATES_DIR / "resume_base.tex")))
