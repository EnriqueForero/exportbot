"""Genera RELEASE_MANIFEST.json (ruta + SHA-256 + bytes de cada archivo).

El notebook Publicar_GitHub lo usa como cédula del release: si a la copia en
Drive le faltan archivos, BLOQUEA el push. Excluye artefactos regenerables.
Uso: python scripts/generar_manifiesto.py  (desde la raíz del repo)
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXCLUIR_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    ".ipynb_checkpoints",
    "resultados",
    "dist",
}
EXCLUIR_ARCHIVOS = {"RELEASE_MANIFEST.json"}
EXCLUIR_SUFIJOS = {".pyc", ".zip", ".log"}


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main() -> None:
    archivos = []
    for p in sorted(RAIZ.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(RAIZ)
        if any(parte in EXCLUIR_DIRS or parte.endswith(".egg-info") for parte in rel.parts):
            continue
        if rel.name in EXCLUIR_ARCHIVOS or p.suffix in EXCLUIR_SUFIJOS:
            continue
        if rel.name in {".coverage", "coverage.xml"}:
            continue
        if rel.name == ".env" or (rel.name.startswith(".env.") and rel.name != ".env.example"):
            continue
        archivos.append({"ruta": str(rel).replace("\\", "/"), "sha256": _sha256(p), "bytes": p.stat().st_size})
    manifiesto = {
        "proyecto": "exportbot",
        "version": (RAIZ / "VERSION").read_text(encoding="utf-8").strip(),
        "generado_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_archivos": len(archivos),
        "archivos": archivos,
    }
    (RAIZ / "RELEASE_MANIFEST.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RELEASE_MANIFEST.json → {len(archivos)} archivos · v{manifiesto['version']}")


if __name__ == "__main__":
    main()
