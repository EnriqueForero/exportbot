"""Pruebas de ExportBot: imports planos (cwd=backend) y entorno limpio."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_VARS_APP = [
    "SF_ACCOUNT",
    "SF_USER",
    "SF_ROLE",
    "SF_WAREHOUSE",
    "SF_DATABASE",
    "SF_SCHEMA",
    "SF_PAT",
    "SF_PRIVATE_KEY_B64_1",
    "SF_PRIVATE_KEY_B64_2",
    "SF_SEMANTIC_VIEW",
    "SF_SEMANTIC_MODEL_FILE",
    "SF_ESQUEMA_TELEMETRIA",
    "TELEMETRIA_ACTIVA",
    "ADMIN_TOKEN",
    "ARRANQUE_ESTRICTO",
    "ESQUEMAS_PERMITIDOS",
    "CORS_ORIGENES",
]


@pytest.fixture()
def entorno_limpio(monkeypatch: pytest.MonkeyPatch):
    """Deja el entorno sin variables de la app para pruebas deterministas."""
    for var in _VARS_APP:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch
