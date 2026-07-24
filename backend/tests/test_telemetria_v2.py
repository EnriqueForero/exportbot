"""Telemetría v2 (DB_EXPORTBOT.TELEMETRY): contrato de columnas y bug de versión.

Estas pruebas leen la cola interna (sin worker ni Snowflake): validan que
cada método arma el INSERT correcto y que la identidad de la app viaja
real — la regresión clave es que UI_EVENT ya no inserta '' como versión.
"""

from __future__ import annotations

from config import VERSION_APP, Config
from snowflake_.ejecutor import Telemetria


def _telemetria(entorno_limpio) -> Telemetria:
    entorno_limpio.setenv("SF_ESQUEMA_TELEMETRIA", "DB_EXPORTBOT.TELEMETRY")
    entorno_limpio.setenv("ENTORNO_APP", "test")
    return Telemetria(Config(), fabrica_conexion=lambda: None)


def test_ui_event_lleva_version_real(entorno_limpio):
    """Regresión del bug b2: log_evento insertaba siempre '' en la versión."""
    t = _telemetria(entorno_limpio)
    t.log_evento("app_inicio", {"auth": "pat"}, session_id="s1", detalle="arranque test")
    sql, params = t._cola.get_nowait()
    assert "UI_EVENT" in sql and "EVENTOS_APP" not in sql
    assert "APP_VERSION" in sql and "ENVIRONMENT" in sql and "USER_ID" in sql
    assert params[0] == VERSION_APP  # versión real, no cadena vacía
    assert params[1] == "test"
    assert params[2] == "anonymous"  # sin usuario declarado → default del estándar


def test_chat_log_guarda_respuesta_y_usuario(entorno_limpio):
    """CHAT_LOG v2: rastro completo pregunta→SQL→respuesta con usuario y entorno."""
    t = _telemetria(entorno_limpio)
    t.log_chat(
        chat_id="c1",
        pregunta="¿Cuánto exportó Antioquia?",
        sql="SELECT 1",
        respuesta="Antioquia exportó X",
        respuesta_degradada=True,
        latencia_redaccion_ms=120,
        user_id="analista@procolombia.co",
    )
    sql, params = t._cola.get_nowait()
    for columna in ("RESPUESTA", "RESPUESTA_DEGRADADA", "LATENCIA_REDACCION_MS", "USER_ID", "ENVIRONMENT", "DETALLES"):
        assert columna in sql
    # 25 columnas: ID + 23 placeholders + PARSE_JSON(%s); TS lo pone CURRENT_TIMESTAMP()
    assert sql.count("%s") == len(params) == 24
    assert "analista@procolombia.co" in params
    assert "Antioquia exportó X" in params


def test_descarga_va_a_download_event_con_chat(entorno_limpio):
    t = _telemetria(entorno_limpio)
    t.log_descarga("c1", "excel", "exportbot_x.xlsx", n_filas=10, n_columnas=3, session_id="s1")
    sql, params = t._cola.get_nowait()
    assert "DOWNLOAD_EVENT" in sql and "CHAT_LOG_ID" in sql
    assert "c1" in params and "excel" in params


def test_middleware_audita_solo_api(entorno_limpio):
    """El middleware registra /api/* en EVENT_LOG y omite los estáticos del SPA."""
    from fastapi.testclient import TestClient

    from main import crear_app

    entorno_limpio.setenv("SF_ESQUEMA_TELEMETRIA", "DB_EXPORTBOT.TELEMETRY")
    entorno_limpio.setenv("ENTORNO_APP", "test")
    with TestClient(crear_app()) as cliente:
        telemetria = cliente.app.state.telemetria
        telemetria.detener()  # sin worker: los INSERT quedan en la cola y se inspeccionan
        telemetria.activa = True  # forzar auditoría aunque no haya conexión real
        while not telemetria._cola.empty():
            telemetria._cola.get_nowait()
        cliente.get("/api/salud", headers={"X-Session-Id": "s-mw", "X-User-Id": "u-mw"})
        sql, params = telemetria._cola.get_nowait()
        assert "EVENT_LOG" in sql and "RESPONSE_STATUS" in sql
        assert "/api/salud" in params and "s-mw" in params and "u-mw" in params
