"""Contrato ejecutable que protege rutas y capacidades de ExportBot."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main as main_mod
from scripts.actualizar_contrato_openapi import build_snapshot

CONTRACT_PATH = ROOT / "contracts" / "exportbot_v2_contract.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_is_versioned_and_nonempty() -> None:
    contract = _contract()
    assert contract["schema_version"] == 1
    assert contract["baseline"].startswith("2.0.0b2")
    assert len(contract["api_routes"]) >= 10
    assert len(contract["frontend_capabilities"]) >= 15
    assert len(contract["backend_invariants"]) >= 8
    matrix = contract["verification_matrix"]
    assert set(matrix["frontend"]) == set(contract["frontend_capabilities"])
    assert set(matrix["backend"]) == set(contract["backend_invariants"])
    assert all(matrix["frontend"].values())
    assert all(matrix["backend"].values())


def test_all_protected_api_routes_still_exist() -> None:
    # OpenAPI es la superficie pública y estable del contrato. ``app.routes`` es
    # una estructura interna de FastAPI/Starlette y puede variar entre versiones
    # aun cuando los endpoints sigan operativos. El gate debe medir el contrato
    # observable, no detalles internos del framework.
    paths = main_mod.crear_app().openapi().get("paths", {})

    missing: list[str] = []
    for expected in _contract()["api_routes"]:
        path = expected["path"]
        expected_methods = {method.lower() for method in expected["methods"]}
        if path not in paths:
            missing.append(f"{path}: ruta ausente")
            continue
        actual_methods = set(paths[path])
        absent_methods = expected_methods - actual_methods
        if absent_methods:
            missing.append(f"{path}: faltan métodos {sorted(method.upper() for method in absent_methods)}")

    assert not missing, "Regresión del contrato API:\n- " + "\n- ".join(missing)


def test_openapi_payload_contract_has_not_changed() -> None:
    baseline_path = ROOT / "contracts" / "openapi_v2_baseline.json"
    expected = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert build_snapshot() == expected, (
        "Regresión del contrato OpenAPI. Si el cambio es intencional, documente, versione, "
        "revise las pruebas y solo entonces regenere con "
        "scripts/actualizar_contrato_openapi.py --confirm-contract-change."
    )


def test_ai_guardrails_and_regression_documentation_exist() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "CONTRATO_DE_REGRESION.md").read_text(encoding="utf-8")
    for phrase in ("Preserve el comportamiento", "gate de regresión", "No modifique una prueba"):
        assert phrase in agents
    for phrase in ("Invariantes funcionales", "Prueba E2E", "Regresión visual"):
        assert phrase in docs
