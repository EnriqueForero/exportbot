"""Cinturones anti-alucinación: validación de SQL y verificación de cifras.

Capa 3 — `validar_sql`: aunque la SQL venga de Cortex Analyst, aquí se
garantiza que sea UNA sola sentencia de solo lectura, sobre esquemas
permitidos y con LIMIT. Capa 5 — `verificar_cifras`: ninguna cifra del
texto redactado puede ser ajena al resultado de la consulta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_PROHIBIDAS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|GRANT|REVOKE|TRUNCATE|CALL|"
    r"COPY|PUT|GET|UNDROP|EXECUTE|USE|COMMENT|DESCRIBE)\b",
    re.IGNORECASE,
)
_RE_LIMIT = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)
_RE_CALIFICADO = re.compile(r"\b([A-Z_][A-Z0-9_$]*)\s*\.\s*([A-Z_][A-Z0-9_$]*)\s*\.", re.IGNORECASE)
_RE_COMENTARIO_LINEA = re.compile(r"--[^\n]*")
_RE_COMENTARIO_BLOQUE = re.compile(r"/\*.*?\*/", re.DOTALL)


@dataclass
class SqlValidada:
    """Resultado de la validación: SQL final o motivo del rechazo."""

    ok: bool
    sql: str = ""
    motivo: str = ""


def _limpiar(sql: str) -> str:
    sql = _RE_COMENTARIO_BLOQUE.sub(" ", sql)
    sql = _RE_COMENTARIO_LINEA.sub(" ", sql)
    return sql.strip().rstrip(";").strip()


def validar_sql(sql_cruda: str, esquemas_permitidos: frozenset[str], max_filas: int) -> SqlValidada:
    """Valida que la SQL sea un único SELECT de solo lectura sobre esquemas permitidos.

    Args:
        sql_cruda: Sentencia propuesta (normalmente por Cortex Analyst).
        esquemas_permitidos: Conjunto ``{"DB.SCHEMA", ...}`` en mayúsculas.
        max_filas: Tope que se fuerza con ``LIMIT`` si la SQL no trae uno.
    """
    sql = _limpiar(sql_cruda)
    if not sql:
        return SqlValidada(ok=False, motivo="SQL vacía.")
    if ";" in sql:
        return SqlValidada(ok=False, motivo="Se rechazan sentencias múltiples (';').")
    inicio = sql.lstrip("( \n\t").upper()
    if not inicio.startswith(("SELECT", "WITH")):
        return SqlValidada(ok=False, motivo="Solo se permiten sentencias SELECT/WITH.")
    m = _PROHIBIDAS.search(sql)
    if m:
        return SqlValidada(ok=False, motivo=f"Palabra clave no permitida: {m.group(1).upper()}.")
    for db, schema in _RE_CALIFICADO.findall(sql):
        par = f"{db}.{schema}".upper()
        if par not in esquemas_permitidos:
            return SqlValidada(ok=False, motivo=f"Esquema fuera de la lista permitida: {par}.")
    if not _RE_LIMIT.search(sql):
        sql = f"SELECT * FROM (\n{sql}\n) LIMIT {int(max_filas)}"
    return SqlValidada(ok=True, sql=sql)


# ── Verificación de cifras ──────────────────────────────────────────────

_RE_NUMERO = re.compile(r"-?\d[\d.,]*")
_ENTERO_PEQUENO_MAX = 100  # ordinales, meses, porcentajes redondos citados
_TOLERANCIA_REL = 1e-6


def _a_float(token: str) -> float | None:
    """Interpreta '1.234.567,89', '1,234,567.89' o '2024' como número."""
    t = token.strip()
    if not t or t in {"-", ".", ","}:
        return None
    if "." in t and "," in t:
        decimal = "," if t.rfind(",") > t.rfind(".") else "."
        miles = "." if decimal == "," else ","
        t = t.replace(miles, "").replace(decimal, ".")
    elif "," in t:
        partes = t.split(",")
        t = t.replace(",", "") if len(partes[-1]) == 3 and len(partes) > 1 else t.replace(",", ".")
    elif t.count(".") > 1 or (t.count(".") == 1 and len(t.split(".")[-1]) == 3 and len(t) > 4):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def _equivalentes(a: float, b: float) -> bool:
    if a == b:
        return True
    escala = max(abs(a), abs(b), 1.0)
    if abs(a - b) <= _TOLERANCIA_REL * escala:
        return True
    # La redacción puede redondear lo que la tabla trae con decimales.
    return any(abs(round(b, d) - a) <= 10 ** (-d) * 0.51 for d in (0, 1, 2))


@dataclass
class VerificacionCifras:
    """Veredicto de la capa 5 con las cifras que no tienen respaldo."""

    ok: bool
    huerfanas: list[str] = field(default_factory=list)


def verificar_cifras(texto: str, filas: list[list[Any]], n_filas: int, pregunta: str = "") -> VerificacionCifras:
    """Comprueba que todo número del texto exista en el resultado (o sea trivial).

    Se permiten: valores de cualquier celda (con redondeos a 0–2 decimales),
    el conteo de filas, los años mencionados en la pregunta y enteros ≤ 100
    (ordinales del tipo "los 10 principales"). Todo lo demás es huérfano.
    """
    permitidos: set[float] = {float(n_filas)}
    for fila in filas:
        for v in fila:
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                permitidos.add(float(v))
                permitidos.add(abs(float(v)))
            elif isinstance(v, str):
                f = _a_float(v)
                if f is not None:
                    permitidos.add(f)
    for token in _RE_NUMERO.findall(pregunta):
        f = _a_float(token)
        if f is not None:
            permitidos.add(f)

    huerfanas: list[str] = []
    for token in _RE_NUMERO.findall(texto):
        f = _a_float(token)
        if f is None:
            continue
        if abs(f) <= _ENTERO_PEQUENO_MAX and float(f).is_integer():
            continue
        if 1900 <= f <= 2100 and float(f).is_integer():
            continue  # años citados en prosa
        if not any(_equivalentes(f, p) for p in permitidos):
            huerfanas.append(token)
    return VerificacionCifras(ok=not huerfanas, huerfanas=huerfanas)
