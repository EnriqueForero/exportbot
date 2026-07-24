"""Orquestador del chat: pregunta → SQL (Analyst) → datos → prosa verificada.

Emite eventos por etapa (para SSE) y termina con un evento ``final``.
Si la ejecución falla, hace UN reintento informándole a Cortex Analyst
el error exacto (lección de gestion_conocimiento). Todo queda en
telemetría, incluida la versión de la fuente semántica usada.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from config import VERSION_APP, Config
from motores.guardas import validar_sql, verificar_cifras
from motores.redactor import plantilla_resumen, redactar
from snowflake_.analyst import ClienteAnalyst, ErrorAnalyst, RespuestaAnalyst
from snowflake_.ejecutor import ResultadoConsulta, Telemetria, ejecutar_select

logger = logging.getLogger(__name__)

_MAX_TURNOS_HISTORIAL = 6  # user+analyst alternados que se reenvían al servicio


class Orquestador:
    """Coordina Analyst, guardas, ejecución, redacción y auditoría."""

    def __init__(
        self,
        cfg: Config,
        fabrica_conexion: Callable[[], Any] | None,
        telemetria: Telemetria,
        cliente_analyst: ClienteAnalyst | None = None,
    ) -> None:
        self._cfg = cfg
        self._fabrica = fabrica_conexion
        self._telemetria = telemetria
        self._analyst = cliente_analyst

    # ------------------------------------------------------------------
    def _evento(self, tipo: str, **datos: Any) -> dict[str, Any]:
        return {"tipo": tipo, **datos}

    def _historial_para_retry(
        self, historial: list[dict[str, Any]], respuesta: RespuestaAnalyst, error: str
    ) -> list[dict[str, Any]]:
        """Agrega el turno del analista y el error exacto para pedir la corrección."""
        nuevo = list(historial)
        contenido = respuesta.contenido_crudo or [{"type": "text", "text": respuesta.interpretacion}]
        nuevo.append({"role": "analyst", "content": contenido})
        nuevo.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "La SQL anterior falló al ejecutarse con este error exacto: "
                            f"{error[:400]}. Corrige la consulta y devuelve solo una nueva SQL válida."
                        ),
                    }
                ],
            }
        )
        return nuevo

    # ------------------------------------------------------------------
    def procesar(
        self,
        pregunta: str,
        historial: list[dict[str, Any]] | None = None,
        proveedor: str = "",
        session_id: str = "",
        user_id: str = "",
    ) -> Iterator[dict[str, Any]]:
        """Genera los eventos del flujo completo para una pregunta.

        Yields:
            Diccionarios con ``tipo`` en {etapa, error, final}.
        """
        cfg = self._cfg
        chat_id = uuid.uuid4().hex
        t0 = time.monotonic()
        pregunta = (pregunta or "").strip()

        if not pregunta:
            yield self._evento("error", chat_id=chat_id, mensaje="La pregunta llegó vacía.")
            return
        if len(pregunta) > cfg.max_caracteres_pregunta:
            yield self._evento(
                "error",
                chat_id=chat_id,
                mensaje=f"La pregunta supera el máximo de {cfg.max_caracteres_pregunta} caracteres.",
            )
            return
        if self._analyst is None or self._fabrica is None:
            yield self._evento(
                "error",
                chat_id=chat_id,
                mensaje="ExportBot está sin conexión a Snowflake (revise credenciales en /api/salud).",
            )
            return

        registro: dict[str, Any] = {
            "chat_id": chat_id,
            "session_id": session_id,
            "user_id": user_id,
            "pregunta": pregunta,
            "version_app": VERSION_APP,
            "version_semantica": cfg.semantic_model_file or cfg.semantic_view,
            "proveedor": proveedor or cfg.proveedor_defecto,
        }

        try:
            # 1) Cortex Analyst → SQL -----------------------------------
            yield self._evento(
                "etapa", chat_id=chat_id, etapa="analyst", detalle="Interpretando la pregunta con Cortex Analyst…"
            )
            t_an = time.monotonic()
            respuesta = self._analyst.preguntar(pregunta, historial)
            registro["latencia_analyst_ms"] = int((time.monotonic() - t_an) * 1000)

            if not respuesta.sql:
                texto = respuesta.interpretacion or (
                    "No pude convertir la pregunta en una consulta sobre la base de exportaciones. "
                    "Intente reformularla con más precisión."
                )
                registro.update(exito=False, error="analyst_sin_sql", respuesta=texto)
                self._log(registro, t0)
                yield self._evento(
                    "final",
                    chat_id=chat_id,
                    texto=texto,
                    sql="",
                    columnas=[],
                    filas=[],
                    n_filas=0,
                    truncado=False,
                    sugerencias=respuesta.sugerencias,
                    meta=self._meta(registro, cifras_ok=True, proveedor="analyst"),
                )
                return

            # 2) Validación de solo lectura ------------------------------
            yield self._evento("etapa", chat_id=chat_id, etapa="validacion", detalle="Validando la SQL generada…")
            intentos = 1
            v = validar_sql(respuesta.sql, cfg.esquemas_permitidos, cfg.max_filas_resultado)
            if not v.ok:
                registro.update(sql=respuesta.sql, sql_validada=False, exito=False, error=f"validacion: {v.motivo}")
                self._log(registro, t0)
                yield self._evento(
                    "error", chat_id=chat_id, mensaje=f"La SQL generada fue rechazada por seguridad: {v.motivo}"
                )
                return
            registro.update(sql=v.sql, sql_validada=True)
            yield self._evento("etapa", chat_id=chat_id, etapa="sql", detalle="SQL validada.", sql=v.sql)

            # 3) Ejecución (con un reintento informando el error) --------
            yield self._evento("etapa", chat_id=chat_id, etapa="ejecucion", detalle="Consultando Snowflake…")
            resultado, error_ejec = self._ejecutar(v.sql)
            if resultado is None:
                intentos = 2
                yield self._evento(
                    "etapa",
                    chat_id=chat_id,
                    etapa="reintento",
                    detalle="La consulta falló; pidiendo corrección al Analyst…",
                )
                try:
                    respuesta2 = self._analyst.preguntar(
                        pregunta, self._historial_para_retry(historial or [], respuesta, error_ejec)
                    )
                except ErrorAnalyst as exc:
                    respuesta2 = RespuestaAnalyst()
                    error_ejec = f"{error_ejec} | reintento: {exc}"
                if respuesta2.sql:
                    v2 = validar_sql(respuesta2.sql, cfg.esquemas_permitidos, cfg.max_filas_resultado)
                    if v2.ok:
                        registro["sql"] = v2.sql
                        yield self._evento("etapa", chat_id=chat_id, etapa="sql", detalle="SQL corregida.", sql=v2.sql)
                        resultado, error_ejec = self._ejecutar(v2.sql)
            registro["intentos"] = intentos
            if resultado is None:
                registro.update(exito=False, error=f"ejecucion: {error_ejec[:400]}")
                self._log(registro, t0)
                yield self._evento(
                    "error", chat_id=chat_id, mensaje=f"La consulta no pudo ejecutarse en Snowflake: {error_ejec[:300]}"
                )
                return
            registro.update(n_filas=resultado.n_filas, latencia_sql_ms=resultado.duracion_ms)
            yield self._evento(
                "etapa",
                chat_id=chat_id,
                etapa="datos",
                detalle=f"{resultado.n_filas} fila(s) obtenidas en {resultado.duracion_ms} ms.",
            )

            # 4) Redacción bajo contrato --------------------------------
            yield self._evento("etapa", chat_id=chat_id, etapa="redaccion", detalle="Redactando la respuesta…")
            t_red = time.monotonic()
            red = redactar(cfg, self._fabrica, proveedor, pregunta, resultado)
            registro.update(proveedor=red.proveedor, modelo=red.modelo)

            # 5) Verificación de cifras ---------------------------------
            verif = verificar_cifras(red.texto, resultado.filas, resultado.n_filas, pregunta)
            if not verif.ok:
                logger.warning("Cifras huérfanas en la redacción (%s); se usa plantilla.", verif.huerfanas[:5])
                red.texto = plantilla_resumen(pregunta, resultado)
                red.proveedor, red.modelo, red.degradado = "plantilla", "", True
            registro.update(
                cifras_ok=verif.ok,
                exito=True,
                respuesta=red.texto,
                respuesta_degradada=red.degradado,
                latencia_redaccion_ms=int((time.monotonic() - t_red) * 1000),
            )
            self._log(registro, t0)

            # 6) Final ---------------------------------------------------
            yield self._evento(
                "final",
                chat_id=chat_id,
                texto=red.texto,
                sql=registro["sql"],
                columnas=resultado.columnas,
                filas=resultado.filas[: cfg.max_filas_cliente],
                n_filas=resultado.n_filas,
                truncado=resultado.truncado or resultado.n_filas > cfg.max_filas_cliente,
                sugerencias=respuesta.sugerencias,
                meta=self._meta(registro, cifras_ok=verif.ok, proveedor=red.proveedor, degradado=red.degradado),
            )
        except ErrorAnalyst as exc:
            registro.update(exito=False, error=f"analyst: {str(exc)[:400]}")
            self._log(registro, t0)
            yield self._evento("error", chat_id=chat_id, mensaje=f"Cortex Analyst no respondió: {str(exc)[:300]}")
        except Exception as exc:
            logger.exception("Fallo inesperado del orquestador")
            registro.update(exito=False, error=f"interno: {str(exc)[:400]}")
            self._log(registro, t0)
            yield self._evento(
                "error", chat_id=chat_id, mensaje="Error interno de ExportBot. El equipo puede auditarlo en telemetría."
            )

    # ------------------------------------------------------------------
    def _ejecutar(self, sql: str) -> tuple[ResultadoConsulta | None, str]:
        try:
            conn = self._fabrica() if self._fabrica else None
            if conn is None:
                return None, "sin conexión"
            return ejecutar_select(conn, sql, self._cfg.max_filas_resultado), ""
        except Exception as exc:  # noqa: BLE001 - el texto viaja al reintento
            return None, str(exc)

    def _meta(
        self, registro: dict[str, Any], *, cifras_ok: bool, proveedor: str, degradado: bool = False
    ) -> dict[str, Any]:
        return {
            "proveedor": proveedor,
            "modelo": registro.get("modelo", ""),
            "degradado": degradado,
            "cifras_verificadas": cifras_ok,
            "latencia_analyst_ms": registro.get("latencia_analyst_ms", 0),
            "latencia_sql_ms": registro.get("latencia_sql_ms", 0),
            "version_app": VERSION_APP,
            "fuente_semantica": registro.get("version_semantica", ""),
            "intentos": registro.get("intentos", 1),
        }

    def _log(self, registro: dict[str, Any], t0: float) -> None:
        registro["latencia_total_ms"] = int((time.monotonic() - t0) * 1000)
        try:
            self._telemetria.log_chat(**registro)
        except Exception:  # noqa: BLE001 - la auditoría nunca rompe el flujo
            logger.warning("No se pudo encolar el registro de telemetría.")
