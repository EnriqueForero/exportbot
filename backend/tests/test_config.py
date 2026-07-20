"""Config: fail-fast, modos de autenticación y esquemas permitidos."""

from config import Config


def test_sin_credenciales_reporta_problemas(entorno_limpio) -> None:
    cfg = Config()
    problemas = cfg.validar()
    assert cfg.modo_auth == "sin_credenciales"
    assert any("SF_ACCOUNT" in p for p in problemas)
    assert any("autenticar" in p for p in problemas)


def test_pat_tiene_prioridad_y_esquemas(entorno_limpio) -> None:
    entorno_limpio.setenv("SF_ACCOUNT", "ORG-CUENTA")
    entorno_limpio.setenv("SF_USER", "SVC_EXPORTBOT")
    entorno_limpio.setenv("SF_WAREHOUSE", "APPS_WH")
    entorno_limpio.setenv("SF_PAT", "token-de-prueba")
    entorno_limpio.setenv("SF_PRIVATE_KEY_B64_1", "no-deberia-usarse")
    entorno_limpio.setenv("SF_ESQUEMA_TELEMETRIA", "BD_EXPORTBOT.TELEMETRIA")
    entorno_limpio.setenv("ESQUEMAS_PERMITIDOS", "otra_db.otro_schema")
    cfg = Config()
    assert cfg.modo_auth == "pat"
    assert cfg.validar() == []
    assert "DWH_PROCOLOMBIA_SNOWFLAKE.SILVER" in cfg.esquemas_permitidos
    assert "OTRA_DB.OTRO_SCHEMA" in cfg.esquemas_permitidos
    assert "BD_EXPORTBOT.TELEMETRIA" in cfg.esquemas_permitidos
    assert cfg.fuente_semantica == {"semantic_view": cfg.semantic_view}
