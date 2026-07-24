"""GET /api/salud — estado operativo sin datos sensibles."""

from __future__ import annotations

from fastapi import APIRouter, Request

from config import VERSION_APP

router = APIRouter(tags=["salud"])


@router.get("/salud")
def salud(request: Request) -> dict:
    """Estado de la app: versión, modo de autenticación y subsistemas."""
    e = request.app.state
    return {
        "estado": "ok" if e.problemas_config == [] else "degradado",
        "version": VERSION_APP,
        "auth_snowflake": e.cfg.modo_auth,
        "cuenta": e.cfg.sf_account,
        "usuario_snowflake": e.cfg.sf_user,
        "llave_rsa": getattr(e, "llave_rsa", ""),
        "llave_rsa_2": getattr(e, "llave_rsa_2", ""),
        "entorno": e.cfg.entorno,
        "fuente_semantica": e.cfg.fuente_semantica,
        "telemetria": bool(e.telemetria.activa),
        "problemas_configuracion": e.problemas_config,
    }
