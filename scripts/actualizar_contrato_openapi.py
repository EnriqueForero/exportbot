"""Genera el snapshot contractual OpenAPI de las rutas protegidas de ExportBot.

No ejecute este script para ocultar un fallo. Úselo únicamente cuando el cambio de
API sea intencional, esté documentado y tenga aprobación de revisión.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import main as main_mod  # noqa: E402

CONTRACT_PATH = ROOT / "contracts" / "exportbot_v2_contract.json"
SNAPSHOT_PATH = ROOT / "contracts" / "openapi_v2_baseline.json"


def build_snapshot() -> dict[str, Any]:
    """Return the canonical OpenAPI subset protected by the regression contract."""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    openapi = main_mod.crear_app().openapi()
    protected_paths: dict[str, Any] = {}

    for route in contract["api_routes"]:
        path = route["path"]
        if path not in openapi["paths"]:
            raise RuntimeError(f"Ruta contractual ausente en OpenAPI: {path}")
        protected_paths[path] = {}
        for method in route["methods"]:
            method_key = method.lower()
            operation = openapi["paths"][path].get(method_key)
            if operation is None:
                raise RuntimeError(f"Método contractual ausente en OpenAPI: {method} {path}")
            protected_paths[path][method_key] = operation

    return {
        "schema_version": 1,
        "application_version": openapi.get("info", {}).get("version"),
        "paths": protected_paths,
        "components": {"schemas": openapi.get("components", {}).get("schemas", {})},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm-contract-change",
        action="store_true",
        help="Confirma que el cambio contractual es intencional, revisado y documentado.",
    )
    args = parser.parse_args()
    if not args.confirm_contract_change:
        raise SystemExit(
            "⛔ No se actualizó el contrato. Use --confirm-contract-change solo tras aprobar un cambio de API intencional."
        )
    snapshot = build_snapshot()
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Contrato OpenAPI actualizado: {SNAPSHOT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
