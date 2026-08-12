"""Pasta pública de materiais gratuitos da landing (`/material_gratuito`)."""
from __future__ import annotations

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
FRONTEND_VUE_DIST = BASE_DIR / "frontend-vue" / "dist"
FRONTEND_VUE_PUBLIC = BASE_DIR / "frontend-vue" / "public"

# Extensões aceitas no upload admin
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".html",
    ".htm",
    ".mp3",
    ".m4a",
    ".wav",
    ".ogg",
    ".aac",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".md",
    ".txt",
}

PROMPT_ALLOWED_EXTENSIONS = {".md", ".txt"}

MAX_UPLOAD_BYTES = 40 * 1024 * 1024  # 40 MB


def material_gratuito_dir(*, create: bool = False) -> Path:
    """
    Diretório servido em /material_gratuito.
    Preferir public/ (fonte em dev); em produção Docker só existe dist/.
    """
    public_dir = FRONTEND_VUE_PUBLIC / "material_gratuito"
    dist_dir = FRONTEND_VUE_DIST / "material_gratuito"
    if public_dir.is_dir() or FRONTEND_VUE_PUBLIC.is_dir():
        target = public_dir
    elif dist_dir.is_dir() or FRONTEND_VUE_DIST.is_dir():
        target = dist_dir
    else:
        target = public_dir
    if create:
        target.mkdir(parents=True, exist_ok=True)
    return target


def sanitize_filename(name: str) -> str:
    base = Path(name or "arquivo").name
    base = base.replace(" ", "-")
    base = re.sub(r"[^A-Za-z0-9._\-]", "", base)
    base = re.sub(r"-{2,}", "-", base).strip(".-")
    if not base:
        base = "arquivo"
    return base[:180]


def public_url_for(filename: str) -> str:
    return f"/material_gratuito/{filename}"
