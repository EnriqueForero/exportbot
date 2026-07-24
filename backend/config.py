"""ExportBot 2.0 — Configuración central del backend.

Toda la parametrización vive aquí y proviene de variables de entorno:
cambiar de base, de vista semántica, de warehouse o de proveedor de
redacción NO exige tocar código (contrato de flexibilidad del proyecto).

Contexto: FastAPI en Railway o en Colab efímero (Cloudflare Tunnel).
Autor: GIC · ProColombia   Fecha: 2026-07-19   Versión: 2.0.0b1
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
ARCHIVO_VERSION = RAIZ_PROYECTO / "VERSION"
VERSION_APP = ARCHIVO_VERSION.read_text(encoding="utf-8").strip() if ARCHIVO_VERSION.exists() else "0.0.0"


def _env(nombre: str, defecto: str = "") -> str:
    """Lee una variable de entorno recortando espacios."""
    return os.getenv(nombre, defecto).strip()


def _env_bool(nombre: str, defecto: bool = False) -> bool:
    """Interpreta una variable de entorno como booleano ('1', 'true', 'si')."""
    crudo = _env(nombre).lower()
    if not crudo:
        return defecto
    return crudo in {"1", "true", "yes", "si", "sí", "on"}


def _env_int(nombre: str, defecto: int) -> int:
    """Lee un entero de entorno; ante valor inválido usa el defecto."""
    try:
        return int(_env(nombre) or defecto)
    except ValueError:
        return defecto


@dataclass(frozen=True)
class Config:
    """Parámetros operativos de ExportBot (inmutables tras el arranque)."""

    # ── Snowflake: identidad y contexto ─────────────────────────────
    sf_account: str = field(default_factory=lambda: _env("SF_ACCOUNT"))
    sf_user: str = field(default_factory=lambda: _env("SF_USER"))
    sf_role: str = field(default_factory=lambda: _env("SF_ROLE"))
    sf_warehouse: str = field(default_factory=lambda: _env("SF_WAREHOUSE"))
    sf_database: str = field(default_factory=lambda: _env("SF_DATABASE", "DWH_PROCOLOMBIA_SNOWFLAKE"))
    sf_schema: str = field(default_factory=lambda: _env("SF_SCHEMA", "SILVER"))
    sf_host: str = field(default_factory=lambda: _env("SF_HOST"))  # opcional: host REST explícito

    # ── Snowflake: autenticación (PAT tiene prioridad; si no, llaves RSA) ──
    sf_pat: str = field(default_factory=lambda: _env("SF_PAT"))
    sf_private_key_b64_1: str = field(default_factory=lambda: _env("SF_PRIVATE_KEY_B64_1"))
    sf_private_key_b64_2: str = field(default_factory=lambda: _env("SF_PRIVATE_KEY_B64_2"))
    sf_key_passphrase_1: str = field(default_factory=lambda: _env("SF_PRIVATE_KEY_PASSPHRASE_1"))
    sf_key_passphrase_2: str = field(default_factory=lambda: _env("SF_PRIVATE_KEY_PASSPHRASE_2"))

    # ── Cortex Analyst: fuente semántica (una de las dos) ───────────
    semantic_view: str = field(
        default_factory=lambda: _env("SF_SEMANTIC_VIEW", "DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.SV_EXPORTACIONES")
    )
    semantic_model_file: str = field(
        default_factory=lambda: _env("SF_SEMANTIC_MODEL_FILE")
    )  # ej. @DB.SCH.STAGE/modelo.yaml

    # ── Redacción de respuestas ─────────────────────────────────────
    # Verificado en la cuenta el 2026-07-23: claude-sonnet-4-6 responde vía
    # SNOWFLAKE.CORTEX.COMPLETE con CORTEX_ENABLED_CROSS_REGION='ANY_REGION'.
    cortex_modelo: str = field(default_factory=lambda: _env("SF_CORTEX_MODELO", "claude-sonnet-4-6"))
    proveedor_defecto: str = field(default_factory=lambda: _env("PROVEEDOR_REDACCION", "cortex"))

    # ── Identidad de la app (telemetría estándar GIC 2026-05-13) ────
    app_nombre: str = field(default_factory=lambda: _env("APP_NOMBRE", "exportbot"))
    entorno: str = field(default_factory=lambda: _env("ENTORNO_APP", "dev"))  # railway | colab | dev
    zona_horaria: str = field(default_factory=lambda: _env("SF_TIMEZONE", "America/Bogota"))

    # ── Telemetría / auditoría ──────────────────────────────────────
    telemetria_activa: bool = field(default_factory=lambda: _env_bool("TELEMETRIA_ACTIVA", True))
    esquema_telemetria: str = field(default_factory=lambda: _env("SF_ESQUEMA_TELEMETRIA", ""))

    # ── Seguridad y límites operativos ──────────────────────────────
    admin_token: str = field(default_factory=lambda: _env("ADMIN_TOKEN"))
    cors_origenes: str = field(default_factory=lambda: _env("CORS_ORIGENES", ""))
    arranque_estricto: bool = field(default_factory=lambda: _env_bool("ARRANQUE_ESTRICTO", False))
    max_filas_resultado: int = field(default_factory=lambda: _env_int("MAX_FILAS_RESULTADO", 5000))
    max_filas_cliente: int = field(default_factory=lambda: _env_int("MAX_FILAS_CLIENTE", 200))
    max_caracteres_pregunta: int = field(default_factory=lambda: _env_int("MAX_CARACTERES_PREGUNTA", 800))
    timeout_sql_s: int = field(default_factory=lambda: _env_int("TIMEOUT_SQL_S", 90))
    timeout_analyst_s: int = field(default_factory=lambda: _env_int("TIMEOUT_ANALYST_S", 60))
    timeout_redaccion_s: int = field(default_factory=lambda: _env_int("TIMEOUT_REDACCION_S", 60))

    # ── Alcance de datos permitido para la SQL generada ─────────────
    esquemas_permitidos_crudo: str = field(default_factory=lambda: _env("ESQUEMAS_PERMITIDOS", ""))

    # ------------------------------------------------------------------
    @property
    def modo_auth(self) -> str:
        """'pat', 'keypair' o 'sin_credenciales' según lo configurado."""
        if self.sf_pat:
            return "pat"
        if self.sf_private_key_b64_1 or self.sf_private_key_b64_2:
            return "keypair"
        return "sin_credenciales"

    @property
    def host_rest(self) -> str:
        """Host base para las APIs REST de Snowflake (Cortex Analyst)."""
        if self.sf_host:
            return self.sf_host
        return f"{self.sf_account}.snowflakecomputing.com"

    @property
    def esquemas_permitidos(self) -> frozenset[str]:
        """Esquemas `DB.SCHEMA` sobre los que la SQL generada puede leer."""
        base = {f"{self.sf_database}.{self.sf_schema}".upper()}
        for pieza in self.esquemas_permitidos_crudo.split(","):
            pieza = pieza.strip().upper()
            if pieza:
                base.add(pieza)
        if self.esquema_telemetria:
            base.add(self.esquema_telemetria.upper())
        return frozenset(base)

    @property
    def fuente_semantica(self) -> dict[str, str]:
        """Cuerpo parcial para la API de Analyst: vista semántica o YAML en stage."""
        if self.semantic_model_file:
            return {"semantic_model_file": self.semantic_model_file}
        return {"semantic_view": self.semantic_view}

    def validar(self) -> list[str]:
        """Fail-fast: devuelve la lista de problemas de configuración.

        Returns:
            Lista de mensajes; vacía si la configuración permite operar
            contra Snowflake. Con ``arranque_estricto`` el llamador debe
            abortar si la lista no está vacía.
        """
        problemas: list[str] = []
        if not self.sf_account:
            problemas.append("SF_ACCOUNT no definido.")
        if not self.sf_user:
            problemas.append("SF_USER no definido.")
        if self.modo_auth == "sin_credenciales":
            problemas.append("Sin SF_PAT ni SF_PRIVATE_KEY_B64_1: no hay forma de autenticar.")
        if not self.sf_warehouse:
            problemas.append("SF_WAREHOUSE no definido.")
        if not (self.semantic_view or self.semantic_model_file):
            problemas.append("Defina SF_SEMANTIC_VIEW o SF_SEMANTIC_MODEL_FILE.")
        if self.telemetria_activa and not self.esquema_telemetria:
            problemas.append("TELEMETRIA_ACTIVA=true exige SF_ESQUEMA_TELEMETRIA (ej. DB_EXPORTBOT.TELEMETRY).")
        return problemas


def cargar_config() -> Config:
    """Construye la configuración leyendo `.env` local si existe (uso dev)."""
    try:  # python-dotenv es opcional en runtime
        from dotenv import load_dotenv

        load_dotenv(RAIZ_PROYECTO / ".env")
    except ModuleNotFoundError:  # pragma: no cover - entorno mínimo
        pass
    return Config()
