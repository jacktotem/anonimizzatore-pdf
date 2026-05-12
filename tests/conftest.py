"""Shared pytest fixtures.

PDF fixtures sono generate da `build_fixtures.py` invece che committate come
binari opachi, così possono essere ispezionate, rigenerate e modificate
riproducibilmente.

Aggiunge `src/` a sys.path così i test possono fare `from app import ...`.
"""
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Permetti import diretto del modulo `app` dai test
sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    """Genera le fixture PDF se mancanti."""
    needed = (
        "plain.pdf",
        "with_js_and_openaction.pdf",
        "with_duplicate_attachments.pdf",
    )
    if not all((FIXTURES_DIR / name).exists() for name in needed):
        subprocess.check_call(
            [sys.executable, str(Path(__file__).parent / "build_fixtures.py")]
        )


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR
