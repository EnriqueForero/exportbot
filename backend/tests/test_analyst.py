"""Parseo defensivo de la respuesta de Cortex Analyst y cuenta para JWT."""

from snowflake_.analyst import _cuenta_para_jwt, parsear_respuesta


def test_parsea_sql_texto_y_sugerencias() -> None:
    cuerpo = {
        "request_id": "abc",
        "message": {
            "role": "analyst",
            "content": [
                {"type": "text", "text": "Interpretación."},
                {"type": "sql", "statement": "SELECT 1"},
                {"type": "suggestions", "suggestions": ["¿Top 10 países?"]},
            ],
        },
        "warnings": [{"message": "aviso"}],
    }
    r = parsear_respuesta(cuerpo)
    assert r.sql == "SELECT 1"
    assert "Interpretación" in r.interpretacion
    assert r.sugerencias == ["¿Top 10 países?"]
    assert r.advertencias == ["aviso"] and r.request_id == "abc"


def test_parseo_tolera_cuerpos_incompletos() -> None:
    r = parsear_respuesta({})
    assert r.sql == "" and r.sugerencias == []


def test_cuenta_para_jwt() -> None:
    assert _cuenta_para_jwt("miorg-cuenta.snowflakecomputing.com") == "MIORG-CUENTA"
    assert _cuenta_para_jwt("ab12345.us-east-1") == "AB12345"
