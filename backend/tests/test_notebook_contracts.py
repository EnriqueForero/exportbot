"""Regression tests for packaging and the two Colab notebooks."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _source(name: str) -> str:
    notebook = json.loads((ROOT / "notebooks" / name).read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])


def test_pyproject_has_explicit_backend_discovery():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[build-system]" in text
    assert 'package-dir = {"" = "backend"}' in text
    assert 'py-modules = ["config", "main", "orquestador", "schemas"]' in text
    assert 'where = ["backend"]' in text


def test_launch_notebook_checks_exportbot_not_legacy_package():
    source = _source("Lanzar_App_Colab_Cloudflare.ipynb")
    assert "registro_analitica" not in source
    assert "version('exportbot')" in source
    for module in ("config", "main", "orquestador", "schemas"):
        assert module in source


def test_publish_notebook_uses_uv_for_install_and_current_tree_contract():
    source = _source("Publicar_GitHub.ipynb")
    assert "registro_analitica/__init__.py" not in source
    assert '"tests"' not in re.search(r"obligatorios = \[.*?\]", source, flags=re.DOTALL).group(0)
    assert '"backend/tests"' in source
    assert '"{venv}/pip"' not in source
    assert '"-r", req_runtime, "-r", req_dev' in source
    assert 'gate_env["PYTHONNOUSERSITE"] = "1"' in source
    assert 'str(GATESRC / "backend")' in source
    assert "main.crear_app().openapi()['paths']" in source
    assert "env=gate_env" in source
    assert "diagnostico.stdout" in source
    assert 'gate_env["PLAYWRIGHT_BROWSERS_PATH"]' in source
    assert 'GATESRC / "scripts" / "playwright_runtime.py"' in source


def test_publish_notebook_reads_current_manifest_schema():
    source = _source("Publicar_GitHub.ipynb")
    assert 'manifiesto.get("archivos")' in source
    assert 'item["ruta"]' in source
    assert 'item["sha256"]' in source
    assert 'manifiesto.get("version")' in source


def test_publish_notebook_blocks_frontend_and_visual_regressions():
    source = _source("Publicar_GitHub.ipynb")
    assert "GATE_COMPLETO = True" in source
    assert '"npm", "--prefix", "frontend", "ci"' in source
    assert '"npm", "--prefix", "frontend", "run", "build"' in source
    assert "backend/tests/test_frontend_e2e.py" in source
    assert "contracts/exportbot_v2_contract.json" in source
    assert "contracts/openapi_v2_baseline.json" in source
    assert "scripts/actualizar_contrato_openapi.py" in source
    assert "backend/tests/visual_baselines/exportbot_inicio.png" in source
    assert "backend/tests/visual_baselines/exportbot_resultado.png" in source


def test_frontend_preserves_diagnostic_attempt_count_and_feedback_purpose():
    source = (ROOT / "frontend" / "src" / "pages" / "ChatPage.tsx").read_text(encoding="utf-8")
    assert "SQL autocorregida (${final.meta.intentos} intentos)" in source
    assert "La calificación alimenta la auditoría de calidad." in source


def test_playwright_runtime_provisions_matching_chromium():
    source = (ROOT / "scripts" / "playwright_runtime.py").read_text(encoding="utf-8")
    assert '"-m", "playwright", "install", "chromium"' in source
    assert '"-m", "playwright", "install-deps", "chromium"' in source
    assert "PLAYWRIGHT_BROWSERS_PATH" in source
    assert "playwright.chromium.launch" in source
