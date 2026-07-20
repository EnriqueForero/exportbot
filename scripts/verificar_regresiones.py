"""Ejecuta el gate único de calidad y regresión de ExportBot.

Uso:
    python scripts/verificar_regresiones.py
    python scripts/verificar_regresiones.py --sin-e2e
    python scripts/verificar_regresiones.py --sin-npm-install
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright_runtime import ensure_chromium

ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    """Run one gate and fail immediately with complete diagnostics."""
    print("  $", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, text=True, env=env)
    if result.returncode != 0:
        raise SystemExit(f"⛔ Gate falló ({result.returncode}): {' '.join(command)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-e2e", action="store_true", help="Omite navegador y comparación visual.")
    parser.add_argument(
        "--sin-npm-install", action="store_true", help="No ejecuta npm ci; exige node_modules existente."
    )
    args = parser.parse_args()
    start = time.time()

    run([sys.executable, "-m", "pytest", "backend/tests", "-m", "not e2e", "-q", "--no-header"])
    run([sys.executable, "-m", "ruff", "check", "backend", "eval", "scripts"])
    run([sys.executable, "-m", "ruff", "format", "--check", "backend", "eval", "scripts"])

    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("⛔ npm no está disponible; se requiere Node.js 20+.")
    frontend = ROOT / "frontend"
    if not args.sin_npm_install:
        run([npm, "ci", "--no-audit", "--no-fund"], cwd=frontend)
    elif not (frontend / "node_modules").exists():
        raise SystemExit("⛔ --sin-npm-install exige frontend/node_modules existente.")
    run([npm, "run", "build"], cwd=frontend)

    if not args.sin_e2e:
        browser_env = ensure_chromium(os.environ.copy())
        run(
            [sys.executable, "-m", "pytest", "backend/tests/test_frontend_e2e.py", "-q", "--no-header"],
            env=browser_env,
        )

    print(f"✅ Gate de regresión completo aprobado en {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
