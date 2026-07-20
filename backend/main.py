"""ExportBot 2.0 — Aplicación FastAPI (API + frontend estático en un servicio).

Arranque tolerante: sin credenciales la app sube en modo degradado y lo
declara en ``/api/salud`` (con ``ARRANQUE_ESTRICTO=true`` aborta). El
build de React (``frontend/dist``) se sirve desde el mismo proceso:
mismo dominio, cero CORS, un solo contenedor en Railway (ADR D5).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from config import RAIZ_PROYECTO, VERSION_APP, cargar_config
from motores.redactor import proveedores_disponibles
from orquestador import Orquestador
from routers import chat, exportar, metricas, salud, track
from snowflake_.analyst import ClienteAnalyst
from snowflake_.conexion import GestorConexion
from snowflake_.ejecutor import Telemetria

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("exportbot")

# El release para Colab trae el build en la RAÍZ (contrato de la plantilla);
# en desarrollo local vive en frontend/dist. Se sirve el primero que exista.
_CANDIDATOS_DIST = (RAIZ_PROYECTO / "frontend" / "dist", RAIZ_PROYECTO / "dist")
DIR_DIST = next((d for d in _CANDIDATOS_DIST if (d / "index.html").exists()), _CANDIDATOS_DIST[0])


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    """Inicializa configuración, conexión, Analyst y telemetría; cierra ordenado."""
    cfg = cargar_config()
    problemas = cfg.validar()
    if problemas:
        mensaje = "Configuración incompleta: " + " | ".join(problemas)
        if cfg.arranque_estricto:
            raise RuntimeError(mensaje)
        logger.warning("%s (la app arranca en modo degradado)", mensaje)

    gestor = GestorConexion(cfg)
    con_credenciales = cfg.modo_auth != "sin_credenciales"
    fabrica = gestor.fabrica() if con_credenciales else None
    telemetria = Telemetria(cfg, fabrica)
    telemetria.iniciar()
    analyst = ClienteAnalyst(cfg) if con_credenciales else None

    app.state.cfg = cfg
    app.state.problemas_config = problemas
    app.state.gestor = gestor
    app.state.telemetria = telemetria
    app.state.orquestador = Orquestador(cfg, fabrica, telemetria, analyst)

    telemetria.log_evento("app_inicio", {"version": VERSION_APP, "auth": cfg.modo_auth})
    logger.info("ExportBot %s listo (auth=%s, telemetria=%s)", VERSION_APP, cfg.modo_auth, telemetria.activa)
    try:
        yield
    finally:
        telemetria.detener()
        gestor.cerrar()


def crear_app() -> FastAPI:
    """Fábrica de la aplicación (facilita pruebas con entornos controlados)."""
    app = FastAPI(title="ExportBot 2.0", version=VERSION_APP, lifespan=ciclo_vida)

    origenes_extra = [o.strip() for o in cargar_config().cors_origenes.split(",") if o.strip()]
    if origenes_extra:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origenes_extra,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    for r in (salud.router, chat.router, exportar.router, metricas.router, track.router):
        app.include_router(r, prefix="/api")

    @app.get("/api/proveedores")
    def proveedores() -> dict:
        """Proveedores de redacción y su disponibilidad (claves solo en servidor)."""
        return {"proveedores": proveedores_disponibles()}

    # ── Frontend estático (SPA) ─────────────────────────────────────
    if (DIR_DIST / "index.html").exists():

        @app.get("/{recurso:path}", include_in_schema=False)
        def spa(recurso: str, request: Request):
            candidato = (DIR_DIST / recurso).resolve()
            if recurso and candidato.is_file() and DIR_DIST.resolve() in candidato.parents:
                return FileResponse(candidato)
            return FileResponse(DIR_DIST / "index.html")

    else:

        @app.get("/", include_in_schema=False)
        def raiz() -> JSONResponse:
            return JSONResponse(
                {
                    "mensaje": "ExportBot 2.0 API en línea. El frontend no está compilado: "
                    "ejecute `npm run build` en frontend/ o use el ZIP de release (trae dist/).",
                    "salud": "/api/salud",
                }
            )

    return app


app = crear_app()
