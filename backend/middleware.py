"""Middleware de auditoría HTTP → ``TELEMETRY.EVENT_LOG`` (estándar GIC).

Registra método, endpoint, status, duración, sesión, usuario, IP y
user-agent de cada request a ``/api/*``. Fail-open por diseño: usa la
cola de :class:`Telemetria`; si la telemetría está inactiva o falla,
el request sigue su curso sin ruido. Los estáticos del SPA no se
registran (señal, no volumen).
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_PREFIJO_AUDITADO = "/api/"


def _ip_cliente(request: Request) -> str:
    """IP real del cliente: primer salto de X-Forwarded-For (Railway/Cloudflare) o el socket."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


class AuditoriaHTTP(BaseHTTPMiddleware):
    """Escribe una fila en EVENT_LOG por cada request de la API."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        inicio = time.monotonic()
        respuesta: Response | None = None
        try:
            respuesta = await call_next(request)
            return respuesta
        finally:
            try:
                ruta = request.url.path
                telemetria = getattr(request.app.state, "telemetria", None)
                if telemetria is not None and telemetria.activa and ruta.startswith(_PREFIJO_AUDITADO):
                    telemetria.log_http(
                        metodo=request.method,
                        endpoint=ruta,
                        status=respuesta.status_code if respuesta is not None else 500,
                        duracion_ms=(time.monotonic() - inicio) * 1000,
                        session_id=request.headers.get("x-session-id", ""),
                        user_id=request.headers.get("x-user-id", ""),
                        client_ip=_ip_cliente(request),
                        user_agent=request.headers.get("user-agent", ""),
                    )
            except Exception:
                logger.debug("Auditoría HTTP omitida por error interno", exc_info=True)
