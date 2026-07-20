"""Adapta las plantillas de notebooks del usuario a ExportBot 2.0 (v3).

Regla de oro: SOLO se editan la Celda A, el encabezado y —desde v3, con
diagnóstico A08— la función ``localizar_proyecto`` y la detección de ``dist``
de la Celda B, que asumían frontend plano (package.json y dist/ en la raíz)
y fallaban con "0 candidatos" ante un monorepo. Cada celda parchada se
valida con ``ast.parse`` antes de escribirse.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ORIGENES = Path("/mnt/user-data/uploads")
DESTINO = Path(__file__).resolve().parent.parent / "notebooks"

CELDA_A_LANZAR = """# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CELDA A — CONFIGURACIÓN (único lugar que se edita)                   ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── 1. De dónde sale el proyecto ─────────────────────────────────────
#     "drive_carpeta": usted descomprimió el ZIP y subió la CARPETA a Drive (recomendado).
#     "drive_zip"    : el ZIP está en Drive y el notebook lo descomprime.
FUENTE_PROYECTO = "drive_carpeta"
RUTA_DRIVE      = "/content/drive/MyDrive/ProColombia/exportbot"
RUTA_ZIP_DRIVE  = "/content/drive/MyDrive/ProColombia/exportbot_v2.0.0b2.zip"  # solo si FUENTE_PROYECTO="drive_zip"

# ── 2. Anatomía de la app (genérico para cualquier FastAPI + frontend) ──
BACKEND_DIR     = "backend"            # carpeta con el ASGI (imports planos → cwd aquí)
APP_ASGI        = "main:app"           # módulo:variable para Uvicorn
RUTA_SALUD      = "/api/salud"         # endpoint que confirma el arranque
PUERTO          = 8000
COMPILAR_FRONTEND = True               # solo actúa si NO llegó dist/ precompilado
NODE_INSTALAR   = "22.12.0"            # versión exacta del tarball oficial si toca instalar
NODE_FALLBACK   = "22"                 # mínimo si package.json no declara "engines"

# ── 3. Entorno de la app ─────────────────────────────────────────────
#     Variables fijas que el backend leerá. Los SECRETOS van en Secrets (🔑).
ENV_APP = {
    "ARRANQUE_ESTRICTO": "false",       # demo: la app sube y declara qué falta en /api/salud
    "PROVEEDOR_REDACCION": "cortex",    # la redacción por defecto no sale de Snowflake
}
#     Secretos de Colab (🔑) que, SI EXISTEN, se pasan al backend con el mismo nombre.
#     Mínimo para operar: SF_ACCOUNT, SF_USER, (SF_PAT o SF_PRIVATE_KEY_B64_1),
#     SF_ROLE, SF_WAREHOUSE y SF_SEMANTIC_VIEW (o SF_SEMANTIC_MODEL_FILE).
SECRETS_PASSTHROUGH = [
    "SF_ACCOUNT", "SF_USER", "SF_PAT",
    "SF_PRIVATE_KEY_B64_1", "SF_PRIVATE_KEY_PASSPHRASE_1",
    "SF_PRIVATE_KEY_B64_2", "SF_PRIVATE_KEY_PASSPHRASE_2",
    "SF_ROLE", "SF_WAREHOUSE", "SF_DATABASE", "SF_SCHEMA", "SF_HOST",
    "SF_SEMANTIC_VIEW", "SF_SEMANTIC_MODEL_FILE",
    "SF_ESQUEMA_TELEMETRIA", "SF_CORTEX_MODELO",
    "ADMIN_TOKEN", "APP_TOKEN",
    "OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY",
    "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
]

# ── 4. Saneo de lockfiles (hallazgo A07.1) ───────────────────────────
#     True: reescribe URLs de espejos privados/file:// a los índices públicos
#     oficiales ANTES de instalar nada (solo en la copia local; su Drive no se toca).
REPARAR_LOCKFILES = True

# ── 5. Rutas del runtime (no suele hacer falta tocarlas) ─────────────
DIR_TRABAJO = "/content/app"        # copia local del proyecto (Drive es lento para I/O)
DIR_LOGS    = "/content/logs"

print("✅ Configuración cargada ·", FUENTE_PROYECTO, "· puerto", PUERTO,
      "· salud", RUTA_SALUD,
      "· saneo de lockfiles", "ON" if REPARAR_LOCKFILES else "OFF")
"""

LOCALIZAR_LANZAR_V3 = '''def localizar_proyecto(raiz: Path) -> Path:
    """Encuentra la carpeta del proyecto (v3: tolera monorepos).

    Marcadores: ``pyproject.toml`` + ``{BACKEND_DIR}/main.py`` +
    ``package.json`` en la raíz **o** en ``frontend/`` (diagnóstico A08).
    """
    raiz = Path(raiz)
    candidatos, pistas = [], []
    for pyproject in raiz.rglob("pyproject.toml"):
        carpeta = pyproject.parent
        if any(parte in IGNORAR_COPIA for parte in carpeta.parts):
            continue
        falta = []
        if not ((carpeta / "package.json").exists()
                or (carpeta / "frontend" / "package.json").exists()):
            falta.append("package.json (en la raíz o en frontend/)")
        if not (carpeta / BACKEND_DIR / "main.py").exists():
            falta.append(f"{BACKEND_DIR}/main.py")
        if falta:
            pistas.append(f"{carpeta} → falta: {', '.join(falta)}")
        else:
            candidatos.append(carpeta)
    if len(candidatos) != 1:
        hijos = ([p.name for p in sorted(raiz.iterdir()) if p.is_dir()][:8]
                 if raiz.exists() else ["(la ruta no existe)"])
        raise RuntimeError(
            f"Se esperaba UN proyecto bajo {raiz} y se encontraron "
            f"{len(candidatos)}: {[str(c) for c in candidatos]}\\n"
            f"  · Subcarpetas de primer nivel vistas: {hijos}\\n"
            f"  · pyproject.toml sin marcadores completos: {pistas[:5] or 'ninguno'}\\n"
            f"  · Requisito: pyproject.toml + {BACKEND_DIR}/main.py + package.json "
            "(raíz o frontend/). Si acaba de subir a Drive, espere a que termine "
            "de sincronizar y reintente."
        )
    return candidatos[0]
'''

LOCALIZAR_PUBLICAR_V3 = '''def localizar_proyecto(raiz=None) -> Path:
    """Encuentra el proyecto (v3, diagnóstico A08: tolera monorepos)."""
    raiz = Path(raiz or RUTA_DRIVE)
    candidatos, pistas = [], []
    for pyproject in raiz.rglob("pyproject.toml"):
        carpeta = pyproject.parent
        if any(p in {"node_modules", ".git", ".venv", "venv"} for p in carpeta.parts):
            continue
        falta = []
        if not ((carpeta / "package.json").exists()
                or (carpeta / "frontend" / "package.json").exists()):
            falta.append("package.json (raíz o frontend/)")
        if not (carpeta / "backend").is_dir():
            falta.append("backend/")
        if falta:
            pistas.append(f"{carpeta} → falta: {', '.join(falta)}")
        else:
            candidatos.append(carpeta)
    if len(candidatos) != 1:
        hijos = ([p.name for p in sorted(raiz.iterdir()) if p.is_dir()][:8]
                 if raiz.exists() else ["(la ruta no existe)"])
        raise RuntimeError(
            f"Se esperaba UN proyecto bajo {raiz}; hay "
            f"{len(candidatos)}: {[str(c) for c in candidatos]}\\n"
            f"  · Subcarpetas vistas: {hijos}\\n"
            f"  · pyproject.toml sin marcadores completos: {pistas[:5] or 'ninguno'}"
        )
    return candidatos[0]
'''


def _leer(nombre: str) -> dict:
    return json.loads((ORIGENES / nombre).read_text(encoding="utf-8"))


def _src(celda: dict) -> str:
    s = celda.get("source", "")
    return "".join(s) if isinstance(s, list) else s


def _poner_src(celda: dict, texto: str) -> None:
    celda["source"] = texto.splitlines(keepends=True)


def _parchear_encabezado(nb: dict, nuevo: str) -> int:
    n = 0
    for celda in nb["cells"]:
        if celda.get("cell_type") != "markdown":
            continue
        s = _src(celda)
        if "configurada para:" in s:
            s = re.sub(r"configurada para:[^\n]*", f"configurada para: {nuevo}", s, count=1)
            s = re.sub(r"Plantilla genérica( ·| \()?\s*v?\d+\)?", "Plantilla genérica · v3", s, count=1)
            _poner_src(celda, s)
            n += 1
            break
    return n


def _celda_con(nb: dict, marca: str) -> dict:
    for celda in nb["cells"]:
        if celda.get("cell_type") == "code" and marca in _src(celda):
            return celda
    raise SystemExit(f"No se encontró la celda con: {marca}")


def _sub(texto: str, patron: str, reemplazo: str, flags: int = 0) -> str:
    nuevo, n = re.subn(patron, reemplazo, texto, count=1, flags=flags)
    if n != 1:
        raise SystemExit(f"Patrón no encontrado (¡plantilla cambió!): {patron[:60]}")
    return nuevo


def _sub_todas(texto: str, patron: str, reemplazo: str) -> tuple[str, int]:
    nuevo, n = re.subn(patron, reemplazo, texto)
    if n < 1:
        raise SystemExit(f"Patrón (todas) no encontrado: {patron[:60]}")
    return nuevo, n


def _parchear_localizar(nb: dict, nueva_funcion: str) -> None:
    """Reemplaza localizar_proyecto completo en la celda que lo define (Celda B)."""
    celda = _celda_con(nb, "def localizar_proyecto")
    s = _src(celda)
    # lambda: el reemplazo es literal (re.sub procesaría los \\n del texto nuevo)
    s, n = re.subn(
        r"def localizar_proyecto.*?return candidatos\[0\]\n", lambda _m: nueva_funcion, s, count=1, flags=re.S
    )
    if n != 1:
        raise SystemExit("No se pudo reemplazar localizar_proyecto")
    ast.parse(s)  # la Celda B parchada debe seguir siendo Python válido
    _poner_src(celda, s)


def adaptar_lanzar() -> None:
    nb = _leer("Lanzar_App_Colab_Cloudflare.ipynb")
    assert (
        _parchear_encabezado(
            nb, "*ExportBot 2.0 (v2.0.0b2) · exportaciones de Colombia · GIC ProColombia · A08: monorepos*"
        )
        == 1
    )
    ast.parse(CELDA_A_LANZAR)
    _poner_src(_celda_con(nb, "CELDA A — CONFIGURACIÓN"), CELDA_A_LANZAR)
    _parchear_localizar(nb, LOCALIZAR_LANZAR_V3)
    pipeline = _celda_con(nb, "def preparar_python")
    ps = _src(pipeline)
    ps = ps.replace("registro_analitica", "config, main, orquestador, schemas")
    ps = ps.replace(
        "import uvicorn, fastapi, config, main, orquestador, schemas",
        "from importlib.metadata import version; assert version('exportbot'); "
        "import uvicorn, fastapi, config, main, orquestador, schemas",
    )
    ast.parse(ps)
    _poner_src(pipeline, ps)
    # dist/ puede venir en la raíz (release) o en frontend/ (build local): ambas valen.
    total = 0
    for celda in nb["cells"]:
        if celda.get("cell_type") != "code":
            continue
        s = _src(celda)
        if '(proyecto / "dist" / "index.html").exists()' in s:
            s, n = _sub_todas(
                s,
                re.escape('(proyecto / "dist" / "index.html").exists()'),
                '((proyecto / "dist" / "index.html").exists() '
                'or (proyecto / "frontend" / "dist" / "index.html").exists())',
            )
            ast.parse(s)
            _poner_src(celda, s)
            total += n
    if total < 1:
        raise SystemExit("No se encontró la comprobación de dist/index.html")
    (DESTINO / "Lanzar_App_Colab_Cloudflare.ipynb").write_text(
        json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"Lanzar v3 OK · celdas: {len(nb['cells'])} · comprobaciones dist parchadas: {total}")


def adaptar_publicar() -> None:
    nb = _leer("Publicar_GitHub.ipynb")
    assert _parchear_encabezado(nb, "`github.com/EnriqueForero/exportbot` · v2.0.0b2 · A08: monorepos") == 1
    celda = _celda_con(nb, "CELDA A — CONFIGURACIÓN")
    s = _src(celda)
    s = _sub(
        s, r'^RUTA_DRIVE\s*=\s*"[^"]*"', 'RUTA_DRIVE         = "/content/drive/MyDrive/ProColombia/exportbot"', re.M
    )
    s = _sub(s, r'^NOMBRE_REPO_GITHUB\s*=\s*"[^"]*"', 'NOMBRE_REPO_GITHUB = "exportbot"', re.M)
    s = _sub(
        s,
        r'DESCRIPCION_REPO\s*=\s*\(.*?"\)',
        'DESCRIPCION_REPO   = ("ExportBot 2.0 — chatbot NL→SQL de exportaciones de Colombia "\n'
        '                      "(FastAPI + Snowflake Cortex Analyst + React). Uso interno · ProColombia.")',
        re.S,
    )
    s = _sub(s, r'^RAMA_TRABAJO\s*=\s*"[^"]*"', 'RAMA_TRABAJO   = "v2-lanzamiento"', re.M)
    s = _sub(
        s,
        r'^MENSAJE_COMMIT\s*=\s*"[^"]*"',
        'MENSAJE_COMMIT = "release: v{version} — ExportBot 2.0 (núcleo F0–F6)"',
        re.M,
    )
    s = _sub(
        s,
        r"GATES_BASE\s*=\s*\[.*?\n\]",
        "GATES_BASE = [          # dependencias instaladas una sola vez en correr_gates\n"
        '    ["{venv}/python", "-m", "pytest", "backend/tests", "-q", "--no-header"],\n'
        "]",
        re.S,
    )
    s = _sub(
        s,
        r"GATES_EXTRA\s*=\s*\[.*?\n\]",
        "GATES_EXTRA = [         # solo con GATE_COMPLETO=True\n"
        '    ["{venv}/ruff", "check", "backend", "eval", "scripts"],\n'
        '    ["{venv}/ruff", "format", "--check", "backend", "eval", "scripts"],\n'
        "]",
        re.S,
    )
    ast.parse(s)
    _poner_src(celda, s)
    _parchear_localizar(nb, LOCALIZAR_PUBLICAR_V3)
    (DESTINO / "Publicar_GitHub.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Publicar v3 OK · celdas: {len(nb['cells'])}")


if __name__ == "__main__":
    DESTINO.mkdir(exist_ok=True)
    adaptar_lanzar()
    adaptar_publicar()
