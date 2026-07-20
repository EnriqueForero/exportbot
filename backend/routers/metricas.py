"""GET /api/metricas/* — dashboard interno PROTEGIDO por token de administración."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

router = APIRouter(tags=["metricas"])


def _exigir_token(request: Request, x_admin_token: str = Header(default="")) -> None:
    """Compara el token en tiempo constante; sin ADMIN_TOKEN el panel queda cerrado."""
    esperado = request.app.state.cfg.admin_token
    if not esperado or not secrets.compare_digest(x_admin_token, esperado):
        raise HTTPException(status_code=401, detail="Token de administración inválido o ausente.")


def _consultar(request: Request, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    estado = request.app.state
    if not estado.telemetria.activa:
        raise HTTPException(status_code=503, detail="Telemetría no configurada en este despliegue.")
    conn = estado.gestor.obtener()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description or []]
        return [dict(zip(cols, fila)) for fila in cur.fetchall()]
    finally:
        cur.close()


@router.get("/metricas/resumen", dependencies=[Depends(_exigir_token)])
def resumen(request: Request) -> dict:
    """KPIs de los últimos 30 días: volumen, éxito, latencias y feedback."""
    e = request.app.state.cfg.esquema_telemetria
    filas = _consultar(
        request,
        f"""SELECT COUNT(*) AS CONSULTAS,
                   COUNT_IF(EXITO) AS EXITOSAS,
                   ROUND(AVG(LATENCIA_TOTAL_MS)) AS LATENCIA_PROM_MS,
                   ROUND(APPROX_PERCENTILE(LATENCIA_TOTAL_MS, 0.95)) AS LATENCIA_P95_MS,
                   COUNT(DISTINCT SESSION_ID) AS SESIONES
            FROM {e}.CHAT_LOG WHERE TS >= DATEADD('day', -30, CURRENT_TIMESTAMP())""",
    )
    fb = _consultar(
        request,
        f"""SELECT COUNT_IF(UTIL) AS POSITIVOS, COUNT_IF(NOT UTIL) AS NEGATIVOS
            FROM {e}.FEEDBACK WHERE TS >= DATEADD('day', -30, CURRENT_TIMESTAMP())""",
    )
    return {"kpis": (filas[0] if filas else {}), "feedback": (fb[0] if fb else {})}


@router.get("/metricas/series", dependencies=[Depends(_exigir_token)])
def series(request: Request) -> dict:
    """Serie diaria de consultas y tasa de éxito (V_CONSULTAS_DIARIAS)."""
    e = request.app.state.cfg.esquema_telemetria
    return {"dias": _consultar(request, f"SELECT * FROM {e}.V_CONSULTAS_DIARIAS ORDER BY DIA DESC LIMIT 60")}


@router.get("/metricas/preguntas", dependencies=[Depends(_exigir_token)])
def preguntas(request: Request) -> dict:
    """Preguntas más frecuentes normalizadas (V_PREGUNTAS_TOP)."""
    e = request.app.state.cfg.esquema_telemetria
    return {"top": _consultar(request, f"SELECT * FROM {e}.V_PREGUNTAS_TOP ORDER BY VECES DESC LIMIT 25")}


@router.get("/metricas/feedback", dependencies=[Depends(_exigir_token)])
def ultimos_feedback(request: Request) -> dict:
    """Últimos comentarios de usuarios, con su pregunta asociada."""
    e = request.app.state.cfg.esquema_telemetria
    sql = f"""SELECT f.TS, f.UTIL, f.COMENTARIO, c.PREGUNTA
              FROM {e}.FEEDBACK f LEFT JOIN {e}.CHAT_LOG c ON f.CHAT_LOG_ID = c.ID
              ORDER BY f.TS DESC LIMIT 30"""
    return {"feedback": _consultar(request, sql)}
