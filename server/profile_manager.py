"""
Local user profile storage.

Uploaded resume files live under data/profile and override the repo template
resume for matching, retrieval, and generation. The template resume remains a
fallback for a fresh clone or a new user who has not uploaded a profile yet.
"""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from pathlib import Path

try:
    from .settings import DATA_DIR, RESUME_PATH, ROOT_DIR
except ImportError:  # pragma: no cover
    from settings import DATA_DIR, RESUME_PATH, ROOT_DIR


PROFILE_DIR = DATA_DIR / "profile"
PROFILE_META_PATH = PROFILE_DIR / "profile.json"
ACTIVE_RESUME_TEX = PROFILE_DIR / "active_resume.tex"
ORIGINAL_RESUME_STEM = "resume_original"

TEXT_EXTENSIONS = {".tex", ".latex", ".txt"}
RESUME_EXTENSIONS = TEXT_EXTENSIONS | {".pdf", ".doc", ".docx"}


def get_active_resume_path() -> Path:
    if ACTIVE_RESUME_TEX.exists():
        return ACTIVE_RESUME_TEX
    return RESUME_PATH


def get_resume_profile() -> dict:
    meta = _read_meta()
    active_path = get_active_resume_path()
    original_path = _find_original_resume()
    return {
        "source": "uploaded" if ACTIVE_RESUME_TEX.exists() else "default",
        "active_resume_path": _display_path(active_path),
        "active_resume_name": meta.get("latex_filename") or active_path.name,
        "has_uploaded_latex": ACTIVE_RESUME_TEX.exists(),
        "has_uploaded_resume": original_path is not None,
        "latex_filename": meta.get("latex_filename", ""),
        "resume_filename": meta.get("resume_filename", ""),
        "updated_at": meta.get("updated_at", ""),
    }


def save_resume_profile(
    *,
    latex_filename: str = "",
    latex_content: str = "",
    resume_filename: str = "",
    resume_content_base64: str = "",
) -> dict:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    clean_latex_name = _safe_filename(latex_filename)
    clean_resume_name = _safe_filename(resume_filename)
    latex_text = latex_content or ""

    if clean_latex_name:
        _validate_extension(clean_latex_name, TEXT_EXTENSIONS, "LaTeX source")
    if clean_resume_name:
        _validate_extension(clean_resume_name, RESUME_EXTENSIONS, "Resume file")

    # If the user only picks one .tex file in the resume slot, treat it as the
    # active LaTeX source as well.
    if not latex_text and clean_resume_name.lower().endswith(tuple(TEXT_EXTENSIONS)) and resume_content_base64:
        latex_text = _decode_text_payload(resume_content_base64)
        clean_latex_name = clean_latex_name or clean_resume_name

    if not latex_text and not ACTIVE_RESUME_TEX.exists():
        raise ValueError("Upload a .tex resume source so matching and generation can use your profile.")

    if latex_text:
        ACTIVE_RESUME_TEX.write_text(latex_text, encoding="utf-8")

    stored_resume = ""
    if clean_resume_name and resume_content_base64:
        ext = Path(clean_resume_name).suffix.lower()
        stored_resume = f"{ORIGINAL_RESUME_STEM}{ext}"
        _remove_existing_originals()
        (PROFILE_DIR / stored_resume).write_bytes(_decode_binary_payload(resume_content_base64))

    meta = {
        "latex_filename": clean_latex_name or _read_meta().get("latex_filename", ACTIVE_RESUME_TEX.name),
        "resume_filename": clean_resume_name or _read_meta().get("resume_filename", ""),
        "stored_resume": stored_resume or _read_meta().get("stored_resume", ""),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    PROFILE_META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return get_resume_profile()


def _read_meta() -> dict:
    if not PROFILE_META_PATH.exists():
        return {}
    try:
        return json.loads(PROFILE_META_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _find_original_resume() -> Path | None:
    for path in PROFILE_DIR.glob(f"{ORIGINAL_RESUME_STEM}.*"):
        if path.is_file():
            return path
    return None


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve()))
    except Exception:
        return path.name


def _remove_existing_originals() -> None:
    for path in PROFILE_DIR.glob(f"{ORIGINAL_RESUME_STEM}.*"):
        if path.is_file():
            path.unlink()


def _safe_filename(filename: str) -> str:
    name = Path(filename or "").name.strip()
    if not name:
        return ""
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name)[:160]


def _validate_extension(filename: str, allowed: set[str], label: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise ValueError(f"{label} must be one of: {allowed_list}")


def _decode_binary_payload(payload: str) -> bytes:
    value = payload.split(",", 1)[1] if "," in payload[:80] else payload
    return base64.b64decode(value)


def _decode_text_payload(payload: str) -> str:
    return _decode_binary_payload(payload).decode("utf-8", errors="replace")
