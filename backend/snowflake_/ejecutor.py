"""Ejecución segura de SELECT y telemetría asíncrona en Snowflake.

`ejecutar_select` corre la SQL (ya validada) con tope de filas y
convierte los valores a tipos JSON-serializables. `Telemetria` registra
cada consulta/evento/feedback mediante una cola en memoria y un worker
único: fail-open — un fallo de auditoría jamás rompe una respuesta.
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
import logging
import queue
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from config import VERSION_APP, Config

logger = logging.getLogger(__name__)

_TAM_COLA = 2000
_SENTINELA = object()


# ── Ejecución de consultas ──────────────────────────────────────────────


@dataclass
class ResultadoConsulta:
    """Resultado tabular listo para serializar al cliente y a los exportadores."""

    columnas: list[str] = field(default_factory=list)
    filas: list[list[Any]] = field(default_factory=list)
    n_filas: int = 0
    truncado: bool = False
    duracion_ms: int = 0


def _celda(valor: Any) -> Any:
    """Convierte un valor del driver a un tipo JSON-serializable."""
    if isinstance(valor, decimal.Decimal):
        return float(valor)
    if isinstance(valor, (dt.datetime, dt.date, dt.time)):
        return valor.isoformat()
    if isinstance(valor, (bytes, bytearray)):
        return valor.decode("utf-8", errors="replace")
    return valor


def ejecutar_select(conexion: Any, sql: str, max_filas: int) -> ResultadoConsulta:
    """Ejecuta un SELECT y devuelve como máximo ``max_filas`` filas.

    Args:
        conexion: Conexión viva del conector de Snowflake.
        sql: Sentencia YA validada por el validador de solo lectura.
        max_filas: Tope duro de filas a traer (protege memoria y red).
    """
    inicio = time.monotonic()
    cursor = conexion.cursor()
    try:
        cursor.execute(sql)
        columnas = [str(d[0]) for d in (cursor.description or [])]
        crudas = cursor.fetchmany(max_filas + 1)
        truncado = len(crudas) > max_filas
        filas = [[_celda(v) for v in fila] for fila in crudas[:max_filas]]
    finally:
        cursor.close()
    return ResultadoConsulta(
        columnas=columnas,
        filas=filas,
        n_filas=len(filas),
        truncado=truncado,
        duracion_ms=int((time.monotonic() - inicio) * 1000),
    )


# ── Telemetría (cola + worker, fail-open) ───────────────────────────────


class Telemetria:
    """Auditoría de uso en Snowflake sin bloquear ni romper el flujo principal."""

    def __init__(self, cfg: Config, fabrica_conexion: Callable[[], Any] | None) -> None:
        self._cfg = cfg
        self._fabrica = fabrica_conexion
        self._cola: queue.Queue[Any] = queue.Queue(maxsize=_TAM_COLA)
        self._worker: threading.Thread | None = None
        self.descartes = 0
        self.activa = bool(cfg.telemetria_activa and cfg.esquema_telemetria and fabrica_conexion)
        # Identidad estándar (GIC 2026-05-13): viaja en TODAS las tablas v2.
        self._app = cfg.app_nombre[:50]
        self._version = VERSION_APP[:16]
        self._entorno = cfg.entorno[:20]

    # -- ciclo de vida ---------------------------------------------------
    def iniciar(self) -> None:
        """Arranca el worker si la telemetría está configurada."""
        if not self.activa or self._worker is not None:
            return
        self._worker = threading.Thread(target=self._consumir, name="telemetria", daemon=True)
        self._worker.start()
        logger.info("Telemetría activa hacia %s", self._cfg.esquema_telemetria)

    def detener(self, espera_s: float = 3.0) -> None:
        """Detiene el worker drenando lo pendiente (best-effort)."""
        if self._worker is None:
            return
        try:
            self._cola.put_nowait(_SENTINELA)
        except queue.Full:
            pass
        self._worker.join(timeout=espera_s)
        self._worker = None

    def _consumir(self) -> None:
        while True:
            item = self._cola.get()
            if item is _SENTINELA:
                return
            sql, params = item
            try:
                conn = self._fabrica() if self._fabrica else None
                if conn is None:
                    continue
                cur = conn.cursor()
                try:
                    cur.execute(sql, params)
                finally:
                    cur.close()
            except Exception as exc:  # noqa: BLE001 - fail-open por diseño
                logger.warning("Telemetría: INSERT falló (%s)", str(exc)[:200])

    def _encolar(self, sql: str, params: tuple[Any, ...]) -> None:
        if not self.activa:
            return
        try:
            self._cola.put_nowait((sql, params))
        except queue.Full:
            self.descartes += 1

    # -- registros (esquema v2: DB_EXPORTBOT.TELEMETRY) ------------------
    def log_chat(self, **campos: Any) -> None:
        """Registra una interacción completa en ``CHAT_LOG`` (una fila por pregunta).

        v2: guarda además la RESPUESTA final entregada, si hubo degradación a
        plantilla, la latencia de redacción, el usuario y el entorno — el
        rastro completo pregunta→SQL→respuesta que exige la auditoría.
        """
        e = self._cfg.esquema_telemetria
        sql = (
            f"INSERT INTO {e}.CHAT_LOG (ID, TS, SESSION_ID, USER_ID, APP_NAME, ENVIRONMENT, "
            "PREGUNTA, SQL_GENERADA, SQL_VALIDADA, EXITO, N_FILAS, RESPUESTA, RESPUESTA_DEGRADADA, "
            "LATENCIA_ANALYST_MS, LATENCIA_SQL_MS, LATENCIA_REDACCION_MS, LATENCIA_TOTAL_MS, "
            "PROVEEDOR_REDACCION, MODELO_REDACCION, CIFRAS_VERIFICADAS, INTENTOS, ERROR, "
            "VERSION_APP, VERSION_SEMANTICA, DETALLES) "
            "SELECT %s, CURRENT_TIMESTAMP(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s)"
        )
        params = (
            campos.get("chat_id", uuid.uuid4().hex),
            campos.get("session_id", "")[:64],
            (campos.get("user_id") or "anonymous")[:200],
            self._app,
            self._entorno,
            campos.get("pregunta", "")[:2000],
            campos.get("sql", "")[:8000],
            bool(campos.get("sql_validada", False)),
            bool(campos.get("exito", False)),
            int(campos.get("n_filas", 0)),
            (campos.get("respuesta") or "")[:8000],
            bool(campos.get("respuesta_degradada", False)),
            int(campos.get("latencia_analyst_ms", 0)),
            int(campos.get("latencia_sql_ms", 0)),
            int(campos.get("latencia_redaccion_ms", 0)),
            int(campos.get("latencia_total_ms", 0)),
            campos.get("proveedor", "")[:64],
            campos.get("modelo", "")[:128],
            bool(campos.get("cifras_ok", True)),
            int(campos.get("intentos", 1)),
            (campos.get("error") or "")[:1000],
            campos.get("version_app", self._version)[:16],
            campos.get("version_semantica", "")[:200],
            json.dumps(campos.get("detalles") or {}, ensure_ascii=False, default=str)[:4000],
        )
        self._encolar(sql, params)

    def log_evento(
        self,
        evento: str,
        detalles: dict[str, Any] | None = None,
        session_id: str = "",
        user_id: str = "",
        detalle: str = "",
        objetivo: str = "",
        pagina: str = "",
    ) -> None:
        """Registra un evento de interfaz/uso en ``UI_EVENT`` (antes EVENTOS_APP).

        Corrige el bug del b2 que insertaba siempre '' como versión: ahora la
        versión, la app y el entorno viajan reales en cada fila.
        """
        e = self._cfg.esquema_telemetria
        sql = (
            f"INSERT INTO {e}.UI_EVENT (APP_VERSION, ENVIRONMENT, USER_ID, SESSION_ID, "
            "EVENT_TYPE, EVENT_DETAIL, EVENT_TARGET, PAGE, PAYLOAD) "
            "SELECT %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s)"
        )
        params = (
            self._version,
            self._entorno,
            (user_id or "anonymous")[:200],
            session_id[:36],
            evento[:64],
            detalle[:200],
            objetivo[:200],
            pagina[:50],
            json.dumps(detalles or {}, ensure_ascii=False, default=str)[:4000],
        )
        self._encolar(sql, params)

    def log_descarga(
        self,
        chat_id: str,
        formato: str,
        nombre_archivo: str = "",
        n_filas: int = 0,
        n_columnas: int = 0,
        session_id: str = "",
        user_id: str = "",
    ) -> None:
        """Registra una descarga (excel/pptx) en ``DOWNLOAD_EVENT`` ligada a su chat."""
        e = self._cfg.esquema_telemetria
        sql = (
            f"INSERT INTO {e}.DOWNLOAD_EVENT (APP_VERSION, ENVIRONMENT, USER_ID, SESSION_ID, "
            "CHAT_LOG_ID, DOWNLOAD_TYPE, FILE_NAME, N_ROWS, N_COLS) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        params = (
            self._version,
            self._entorno,
            (user_id or "anonymous")[:200],
            session_id[:36],
            chat_id[:64],
            formato[:20],
            nombre_archivo[:200],
            int(n_filas),
            int(n_columnas),
        )
        self._encolar(sql, params)

    def log_feedback(
        self, chat_id: str, util: bool, comentario: str = "", session_id: str = "", user_id: str = ""
    ) -> None:
        """Registra el pulgar arriba/abajo del usuario en ``FEEDBACK``."""
        e = self._cfg.esquema_telemetria
        sql = (
            f"INSERT INTO {e}.FEEDBACK (CHAT_LOG_ID, UTIL, COMENTARIO, USER_ID, SESSION_ID, APP_NAME) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        self._encolar(
            sql,
            (chat_id[:64], bool(util), comentario[:1000], (user_id or "anonymous")[:200], session_id[:36], self._app),
        )

    def log_http(
        self,
        metodo: str,
        endpoint: str,
        status: int,
        duracion_ms: float,
        session_id: str = "",
        user_id: str = "",
        client_ip: str = "",
        user_agent: str = "",
    ) -> None:
        """Registra un request HTTP en ``EVENT_LOG`` (lo llama el middleware)."""
        e = self._cfg.esquema_telemetria
        sql = (
            f"INSERT INTO {e}.EVENT_LOG (APP_VERSION, ENVIRONMENT, USER_ID, SESSION_ID, "
            "CLIENT_IP, USER_AGENT, METHOD, ENDPOINT, RESPONSE_STATUS, RESPONSE_TIME_MS) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        params = (
            self._version,
            self._entorno,
            (user_id or "anonymous")[:200],
            session_id[:36],
            client_ip[:45],
            user_agent[:500],
            metodo[:10],
            endpoint[:200],
            int(status),
            round(float(duracion_ms), 2),
        )
        self._encolar(sql, params)
