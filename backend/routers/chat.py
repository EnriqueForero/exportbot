"""POST /api/chat — flujo completo por SSE (eventos de etapa + final)."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from schemas import PreguntaEntrada

router = APIRouter(tags=["chat"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("/chat")
def chat(entrada: PreguntaEntrada, request: Request) -> StreamingResponse:
    """Procesa la pregunta y transmite los eventos del orquestador como SSE."""
    orq = request.app.state.orquestador

    def flujo() -> Iterator[str]:
        for evento in orq.procesar(
            pregunta=entrada.pregunta,
            historial=entrada.historial,
            proveedor=entrada.proveedor,
            session_id=entrada.session_id,
            user_id=entrada.user_id or request.headers.get("x-user-id", ""),
        ):
            yield "data: " + json.dumps(evento, ensure_ascii=False, default=str) + "\n\n"

    return StreamingResponse(flujo(), media_type="text/event-stream", headers=_SSE_HEADERS)
