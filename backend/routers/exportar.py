"""POST /api/exportar/{excel|pptx} — archivos institucionales server-side."""

from __future__ import annotations

from datetime import datetime

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
    request.app.state.telemetria.log_evento(
        "descarga_excel", {"chat_id": entrada.chat_id, "n_filas": len(entrada.filas)}, entrada.session_id
    )
    return _respuesta(contenido, f"exportbot_{datetime.now():%Y%m%d_%H%M}.xlsx", _MIME_XLSX)


@router.post("/exportar/pptx")
def exportar_pptx(entrada: ExportEntrada, request: Request) -> Response:
    """Construye la presentación institucional del resultado y registra la descarga."""
    contenido = pptx.construir(entrada.pregunta, entrada.texto, entrada.sql, entrada.columnas, entrada.filas)
    request.app.state.telemetria.log_evento(
        "descarga_pptx", {"chat_id": entrada.chat_id, "n_filas": len(entrada.filas)}, entrada.session_id
    )
    return _respuesta(contenido, f"exportbot_{datetime.now():%Y%m%d_%H%M}.pptx", _MIME_PPTX)
