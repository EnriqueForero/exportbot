"""Redacción de respuestas bajo contrato multi-proveedor.

La SQL SIEMPRE proviene de Cortex Analyst (decisión D7 del plan); aquí
solo se convierte el resultado tabular en prosa. Proveedores: ``cortex``
(SNOWFLAKE.CORTEX.COMPLETE, los datos no salen de la cuenta) y cualquier
API compatible con OpenAI (Gemini, Groq, OpenRouter, OpenAI…) con la
clave SOLO en el servidor. Fallback: proveedor pedido → cortex →
plantilla determinista sin LLM.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

from config import Config
from snowflake_.ejecutor import ResultadoConsulta

logger = logging.getLogger(__name__)

_MAX_FILAS_PROMPT = 30
_MAX_TOKENS_SALIDA = 700

#: Catálogo editable por entorno: PROVEEDOR_<ID>_BASE_URL / _API_KEY / _MODELO.
PROVEEDORES: dict[str, dict[str, str]] = {
    "cortex": {"nombre": "Snowflake Cortex", "base_url": "", "env_key": "", "modelo": ""},
    "openai": {
        "nombre": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "modelo": "gpt-4o-mini",
    },
    "gemini": {
        "nombre": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "modelo": "gemini-2.5-flash",
    },
    "groq": {
        "nombre": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "modelo": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "nombre": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "modelo": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "anthropic": {
        "nombre": "Anthropic (compat.)",
        "base_url": "https://api.anthropic.com/v1",
        "env_key": "ANTHROPIC_API_KEY",
        "modelo": "claude-3-5-haiku-latest",
    },
}


def _config_proveedor(pid: str) -> tuple[str, str, str]:
    """Resuelve (base_url, api_key, modelo) del proveedor, con overrides de entorno."""
    base = PROVEEDORES.get(pid, {})
    pref = f"PROVEEDOR_{pid.upper()}_"
    base_url = os.getenv(pref + "BASE_URL", base.get("base_url", "")).rstrip("/")
    api_key = os.getenv(pref + "API_KEY", "") or os.getenv(base.get("env_key", ""), "")
    modelo = os.getenv(pref + "MODELO", base.get("modelo", ""))
    return base_url, api_key, modelo


def proveedores_disponibles() -> list[dict[str, str]]:
    """Lista para la interfaz: id, nombre y si hay clave configurada."""
    salida: list[dict[str, str]] = []
    for pid, info in PROVEEDORES.items():
        _, key, modelo = _config_proveedor(pid)
        disponible = "si" if (pid == "cortex" or key) else "no"
        salida.append({"id": pid, "nombre": info["nombre"], "modelo": modelo, "disponible": disponible})
    return salida


# ── Prompt y plantilla ──────────────────────────────────────────────────


def _tabla_markdown(res: ResultadoConsulta) -> str:
    filas = res.filas[:_MAX_FILAS_PROMPT]
    cab = " | ".join(res.columnas)
    sep = " | ".join("---" for _ in res.columnas)
    cuerpo = "\n".join(" | ".join("" if v is None else str(v) for v in f) for f in filas)
    extra = f"\n(… {res.n_filas - len(filas)} filas más no mostradas)" if res.n_filas > len(filas) else ""
    return f"{cab}\n{sep}\n{cuerpo}{extra}"


def construir_prompt(pregunta: str, res: ResultadoConsulta) -> str:
    """Prompt de redacción con el contrato anti-alucinación explícito."""
    return (
        "Eres el redactor de ExportBot (ProColombia). Responde en español, en 2 a 5 "
        "frases claras y profesionales, la pregunta del usuario usando EXCLUSIVAMENTE "
        "los datos de la tabla adjunta (resultado ya calculado en Snowflake).\n"
        "CONTRATO OBLIGATORIO: (1) no inventes ni calcules cifras nuevas — cita solo "
        "valores presentes en la tabla, redondeando si acaso a máximo 2 decimales; "
        "(2) los valores monetarios son dólares FOB (USD); (3) si la tabla está vacía "
        "o no responde la pregunta, dilo explícitamente y no especules; (4) no "
        "menciones SQL ni tecnicismos internos.\n\n"
        f"Pregunta del usuario: {pregunta}\n\nTabla de resultados ({res.n_filas} filas):\n"
        f"{_tabla_markdown(res)}\n\nRespuesta:"
    )


def plantilla_resumen(pregunta: str, res: ResultadoConsulta) -> str:
    """Resumen determinista (sin LLM) usado como último recurso seguro."""
    if res.n_filas == 0:
        return "La consulta se ejecutó correctamente pero no arrojó filas para esa combinación de filtros."
    primera = ", ".join(f"{c}: {v}" for c, v in zip(res.columnas, res.filas[0]))
    base = f"La consulta devolvió {res.n_filas} fila(s). Primer registro → {primera}."
    if res.truncado:
        base += " El resultado fue truncado al tope configurado; refine los filtros para ver más."
    return base + " Revise la tabla adjunta para el detalle completo."


# ── Ejecución por proveedor ─────────────────────────────────────────────


def _redactar_cortex(fabrica_conexion: Callable[[], Any], modelo: str, prompt: str) -> str:
    conn = fabrica_conexion()
    cur = conn.cursor()
    try:
        cur.execute("SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s)", (modelo, prompt))
        fila = cur.fetchone()
    finally:
        cur.close()
    return str(fila[0]).strip() if fila and fila[0] else ""


def _redactar_openai_compat(base_url: str, api_key: str, modelo: str, prompt: str, timeout_s: int) -> str:
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": _MAX_TOKENS_SALIDA,
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    datos = resp.json()
    return str(datos["choices"][0]["message"]["content"]).strip()


@dataclass
class Redaccion:
    """Texto final junto con el proveedor efectivamente usado."""

    texto: str
    proveedor: str
    modelo: str
    degradado: bool = False  # True si se cayó al fallback


def redactar(
    cfg: Config,
    fabrica_conexion: Callable[[], Any] | None,
    proveedor_pedido: str,
    pregunta: str,
    res: ResultadoConsulta,
) -> Redaccion:
    """Redacta la respuesta con cadena de fallback pedido → cortex → plantilla."""
    prompt = construir_prompt(pregunta, res)
    intentos: list[str] = []
    pedido = (proveedor_pedido or cfg.proveedor_defecto or "cortex").lower()
    for pid in [pedido] + (["cortex"] if pedido != "cortex" else []):
        try:
            if pid == "cortex":
                if fabrica_conexion is None:
                    raise RuntimeError("Sin conexión Snowflake para Cortex COMPLETE.")
                texto = _redactar_cortex(fabrica_conexion, cfg.cortex_modelo, prompt)
                if texto:
                    return Redaccion(
                        texto=texto, proveedor="cortex", modelo=cfg.cortex_modelo, degradado=bool(intentos)
                    )
            else:
                base_url, api_key, modelo = _config_proveedor(pid)
                if not (base_url and api_key and modelo):
                    raise RuntimeError(f"Proveedor '{pid}' sin configurar (clave/modelo).")
                texto = _redactar_openai_compat(base_url, api_key, modelo, prompt, cfg.timeout_redaccion_s)
                if texto:
                    return Redaccion(texto=texto, proveedor=pid, modelo=modelo, degradado=bool(intentos))
            raise RuntimeError("Respuesta vacía del proveedor.")
        except Exception as exc:  # noqa: BLE001 - se degrada de forma controlada
            intentos.append(f"{pid}: {str(exc)[:150]}")
            logger.warning("Redacción falló con '%s': %s", pid, str(exc)[:200])
    return Redaccion(texto=plantilla_resumen(pregunta, res), proveedor="plantilla", modelo="", degradado=True)
