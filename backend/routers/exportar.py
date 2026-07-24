"""POST /api/exportar/{excel|pptx} — archivos institucionales server-side."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_TZ_BOGOTA = ZoneInfo("America/Bogota")

from fastapi import APIRouter, Request
from fastapi.responses import Response

from exportadores import excel, pptx
from schemas import ExportEntrada

router = APIRouter(tags=["exportar"])

_MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_MIME_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _respuesta(contenido: bytes, nombre: str, mime: str) -> Response:
    return Response(
        content=contenido,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/exportar/excel")
def exportar_excel(entrada: ExportEntrada, request: Request) -> Response:
    """Construye el Excel institucional del resultado y registra la descarga."""
    contenido = excel.construir(entrada.pregunta, entrada.texto, entrada.sql, entrada.columnas, entrada.filas)
    nombre = f"exportbot_{datetime.now(_TZ_BOGOTA):%Y%m%d_%H%M}.xlsx"
    request.app.state.telemetria.log_descarga(
        entrada.chat_id, "excel", nombre, len(entrada.filas), len(entrada.columnas), entrada.session_id, entrada.user_id
    )
    return _respuesta(contenido, nombre, _MIME_XLSX)


@router.post("/exportar/pptx")
def exportar_pptx(entrada: ExportEntrada, request: Request) -> Response:
    """Construye la presentación institucional del resultado y registra la descarga."""
    contenido = pptx.construir(entrada.pregunta, entrada.texto, entrada.sql, entrada.columnas, entrada.filas)
    nombre = f"exportbot_{datetime.now(_TZ_BOGOTA):%Y%m%d_%H%M}.pptx"
    request.app.state.telemetria.log_descarga(
        entrada.chat_id, "pptx", nombre, len(entrada.filas), len(entrada.columnas), entrada.session_id, entrada.user_id
    )
    return _respuesta(contenido, nombre, _MIME_PPTX)
