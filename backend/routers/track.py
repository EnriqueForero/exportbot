"""POST /api/track/* — feedback y eventos reportados por el frontend."""

from __future__ import annotations

from fastapi import APIRouter, Request

from schemas import EventoEntrada, FeedbackEntrada

router = APIRouter(tags=["track"])


@router.post("/track/feedback")
def feedback(entrada: FeedbackEntrada, request: Request) -> dict:
    """Registra el pulgar arriba/abajo (insumo directo de calidad)."""
    request.app.state.telemetria.log_feedback(
        entrada.chat_id, entrada.util, entrada.comentario, entrada.session_id, entrada.user_id
    )
    return {"ok": True}


@router.post("/track/evento")
def evento(entrada: EventoEntrada, request: Request) -> dict:
    """Registra un evento de uso libre del frontend."""
    request.app.state.telemetria.log_evento(
        entrada.evento,
        entrada.detalles,
        entrada.session_id,
        user_id=entrada.user_id,
        detalle=entrada.detalle,
        objetivo=entrada.objetivo,
        pagina=entrada.pagina,
    )
    return {"ok": True}
