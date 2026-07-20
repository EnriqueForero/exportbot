"""API en modo degradado: salud, exportar y protección de /metricas."""

from fastapi.testclient import TestClient

import main as main_mod


def _cliente(entorno_limpio) -> TestClient:
    return TestClient(main_mod.crear_app())


def test_salud_en_modo_degradado(entorno_limpio) -> None:
    with _cliente(entorno_limpio) as cliente:
        r = cliente.get("/api/salud")
        assert r.status_code == 200
        datos = r.json()
        assert datos["estado"] == "degradado"
        assert datos["auth_snowflake"] == "sin_credenciales"


def test_chat_sin_credenciales_devuelve_error_claro(entorno_limpio) -> None:
    with _cliente(entorno_limpio) as cliente:
        r = cliente.post("/api/chat", json={"pregunta": "total 2024"})
        assert r.status_code == 200
        assert '"tipo": "error"' in r.text and "credenciales" in r.text.lower() or "conexión" in r.text.lower()


def test_exportar_excel_funciona_sin_snowflake(entorno_limpio) -> None:
    with _cliente(entorno_limpio) as cliente:
        r = cliente.post(
            "/api/exportar/excel",
            json={"pregunta": "p", "texto": "t", "sql": "SELECT 1", "columnas": ["A"], "filas": [[1]]},
        )
        assert r.status_code == 200 and r.content[:2] == b"PK"


def test_metricas_exige_token(entorno_limpio) -> None:
    with _cliente(entorno_limpio) as cliente:
        assert cliente.get("/api/metricas/resumen").status_code == 401
    entorno_limpio.setenv("ADMIN_TOKEN", "secreto")
    with _cliente(entorno_limpio) as cliente:
        r = cliente.get("/api/metricas/resumen", headers={"X-Admin-Token": "secreto"})
        assert r.status_code == 503  # token válido, telemetría sin configurar


def test_proveedores_lista_cortex(entorno_limpio) -> None:
    with _cliente(entorno_limpio) as cliente:
        datos = cliente.get("/api/proveedores").json()
        ids = [p["id"] for p in datos["proveedores"]]
        assert "cortex" in ids
