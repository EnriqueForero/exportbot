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

from config import Config

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

    # -- registros -------------------------------------------------------
    def log_chat(self, **campos: Any) -> None:
        """Registra una interacción completa en ``CHAT_LOG`` (una fila por pregunta)."""
        e = self._cfg.esquema_telemetria
        sql = (
            f"INSERT INTO {e}.CHAT_LOG (ID, TS, SESSION_ID, PREGUNTA, SQL_GENERADA, "
            "SQL_VALIDADA, EXITO, N_FILAS, LATENCIA_ANALYST_MS, LATENCIA_SQL_MS, "
            "LATENCIA_TOTAL_MS, PROVEEDOR_REDACCION, MODELO_REDACCION, CIFRAS_VERIFICADAS, "
            "INTENTOS, ERROR, VERSION_APP, VERSION_SEMANTICA) "
            "VALUES (%s, CURRENT_TIMESTAMP(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        params = (
            campos.get("chat_id", uuid.uuid4().hex),
            campos.get("session_id", ""),
            campos.get("pregunta", "")[:2000],
            campos.get("sql", "")[:4000],
            bool(campos.get("sql_validada", False)),
            bool(campos.get("exito", False)),
            int(campos.get("n_filas", 0)),
            int(campos.get("latencia_analyst_ms", 0)),
            int(campos.get("latencia_sql_ms", 0)),
            int(campos.get("latencia_total_ms", 0)),
            campos.get("proveedor", "")[:64],
            campos.get("modelo", "")[:128],
            bool(campos.get("cifras_ok", True)),
            int(campos.get("intentos", 1)),
            (campos.get("error") or "")[:1000],
            campos.get("version_app", "")[:16],
            campos.get("version_semantica", "")[:120],
        )
        self._encolar(sql, params)

    def log_evento(self, evento: str, detalles: dict[str, Any] | None = None, session_id: str = "") -> None:
        """Registra un evento de uso (descargas, arranques, accesos) en ``EVENTOS_APP``."""
        e = self._cfg.esquema_telemetria
        sql = (
            f"INSERT INTO {e}.EVENTOS_APP (TS, SESSION_ID, EVENTO, DETALLES, VERSION_APP) "
            "SELECT CURRENT_TIMESTAMP(), %s, %s, PARSE_JSON(%s), %s"
        )
        self._encolar(sql, (session_id, evento[:64], json.dumps(detalles or {}, ensure_ascii=False)[:4000], ""))

    def log_feedback(self, chat_id: str, util: bool, comentario: str = "") -> None:
        """Registra el pulgar arriba/abajo del usuario en ``FEEDBACK``."""
        e = self._cfg.esquema_telemetria
        sql = f"INSERT INTO {e}.FEEDBACK (TS, CHAT_LOG_ID, UTIL, COMENTARIO) VALUES (CURRENT_TIMESTAMP(), %s, %s, %s)"
        self._encolar(sql, (chat_id[:64], bool(util), comentario[:1000]))
