"""Provisiona y valida Chromium para los gates E2E de ExportBot.

El paquete Python de Playwright y sus navegadores son artefactos separados. Este
script garantiza que el navegador compatible con la versión instalada esté
presente antes de ejecutar pytest. Es idempotente y reutiliza el caché del
runtime.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROBE = r"""
import os
import shutil
from playwright.sync_api import sync_playwright

explicit = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
system = (
    explicit
    or shutil.which("chromium")
    or shutil.which("chromium-browser")
    or shutil.which("google-chrome")
)
kwargs = {"headless": True}
if system:
    kwargs["executable_path"] = system
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(**kwargs)
    print(
        "chromium=",
        browser.version,
        "origen=",
        system or os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "cache-default"),
    )
    browser.close()
"""


def playwright_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    """Devuelve un entorno coherente para instalación y ejecución de Playwright."""
    env = dict(base or os.environ)
    if not env.get("PLAYWRIGHT_BROWSERS_PATH"):
        if Path("/content").exists():
            cache = Path("/content/.cache/ms-playwright")
        else:
            cache = Path.home() / ".cache/ms-playwright"
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(cache)
    Path(env["PLAYWRIGHT_BROWSERS_PATH"]).expanduser().mkdir(parents=True, exist_ok=True)
    return env


def _run(
    command: list[str],
    env: dict[str, str],
    timeout: int = 900,
) -> subprocess.CompletedProcess[str]:
    shown = " ".join(command)
    if len(command) >= 3 and command[1] == "-c":
        shown = f"{command[0]} -c <probe Chromium>"
    print("  $", shown, flush=True)
    return subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
        env=env,
        timeout=timeout,
    )


def _probe(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, "-c", PROBE], env=env, timeout=120)


def _tail(result: subprocess.CompletedProcess[str], limit: int = 2500) -> str:
    return ((result.stdout or "") + (result.stderr or ""))[-limit:]


def ensure_chromium(env: dict[str, str] | None = None) -> dict[str, str]:
    """Garantiza un Chromium arrancable y devuelve el entorno que debe heredarse."""
    effective = playwright_environment(env)
    first = _probe(effective)
    if first.returncode == 0:
        print("🌐 Chromium de Playwright disponible · " + (first.stdout or "").strip())
        return effective

    print("🌐 Chromium no está disponible; instalando la versión compatible con Playwright…")
    install = _run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        env=effective,
    )
    if install.returncode != 0:
        raise RuntimeError("No se pudo descargar Chromium para Playwright:\n" + _tail(install))

    second = _probe(effective)
    if second.returncode == 0:
        print("✅ Chromium instalado y validado · " + (second.stdout or "").strip())
        return effective

    # Algunos Linux mínimos tienen el binario pero carecen de bibliotecas del SO.
    # En Colab el proceso corre como root, por lo que Playwright puede instalar sus
    # dependencias oficiales. En otros entornos se conserva el diagnóstico exacto.
    can_install_deps = hasattr(os, "geteuid") and os.geteuid() == 0 and shutil.which("apt-get") is not None
    if can_install_deps:
        print("🧩 Faltan dependencias del sistema; instalando dependencias oficiales de Chromium…")
        deps = _run(
            [sys.executable, "-m", "playwright", "install-deps", "chromium"],
            env=effective,
            timeout=1200,
        )
        if deps.returncode != 0:
            raise RuntimeError("No se pudieron instalar dependencias del sistema para Chromium:\n" + _tail(deps))
        third = _probe(effective)
        if third.returncode == 0:
            print("✅ Chromium y dependencias validados · " + (third.stdout or "").strip())
            return effective
        second = third

    raise RuntimeError(
        "Chromium fue instalado, pero no pudo arrancar. Diagnóstico:\n" + _tail(second) + "\nEjecute manualmente: "
        "python -m playwright install --with-deps chromium"
    )


def main() -> None:
    ensure_chromium()


if __name__ == "__main__":
    main()
