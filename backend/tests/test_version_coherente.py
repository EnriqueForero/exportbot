"""La versión vive en UN solo número — vigilado.

Incidente 2026-07-24: pyproject.toml quedó en 2.0.0b2 mientras VERSION
avanzaba a rc3; el publicador de GitHub (correctamente) bloqueó el release
por incoherencia. Este test hace imposible repetirlo: cualquier bump
parcial rompe la suite, que corre en todos los gates.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_version_unica_en_todo_el_repo():
    v = (RAIZ / "VERSION").read_text(encoding="utf-8").strip()
    py = re.search(
        r'^version\s*=\s*"([^"]+)"', (RAIZ / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE
    ).group(1)
    pkg = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))["version"]
    fpkg = json.loads((RAIZ / "frontend" / "package.json").read_text(encoding="utf-8"))["version"]
    assert v == py == pkg == fpkg, (
        f"Versiones divergentes: VERSION={v} · pyproject={py} · package.json={pkg} · frontend={fpkg}. "
        "Actualice las cuatro en el mismo commit (o use un solo bump script)."
    )
