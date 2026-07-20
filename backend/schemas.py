"""Modelos Pydantic de entrada/salida de la API de ExportBot."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PreguntaEntrada(BaseModel):
    """Cuerpo de POST /api/chat."""

    pregunta: str = Field(..., min_length=1, max_length=2000)
    historial: list[dict[str, Any]] = Field(default_factory=list)
    proveedor: str = ""
    session_id: str = Field(default="", max_length=64)


class ExportEntrada(BaseModel):
    """Cuerpo de POST /api/exportar/{excel|pptx}: la tarjeta se exporta a sí misma."""

    pregunta: str = ""
    texto: str = ""
    sql: str = ""
    columnas: list[str] = Field(default_factory=list)
    filas: list[list[Any]] = Field(default_factory=list)
    chat_id: str = ""
    session_id: str = ""


class FeedbackEntrada(BaseModel):
    """Pulgar arriba/abajo sobre una respuesta."""

    chat_id: str = Field(..., min_length=4, max_length=64)
    util: bool
    comentario: str = Field(default="", max_length=1000)
    session_id: str = ""


class EventoEntrada(BaseModel):
    """Evento libre reportado por el frontend."""

    evento: str = Field(..., min_length=1, max_length=64)
    detalles: dict[str, Any] = Field(default_factory=dict)
    session_id: str = ""
