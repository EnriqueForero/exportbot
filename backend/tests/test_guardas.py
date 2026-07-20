"""Guardas anti-alucinación: validador de SQL y verificador de cifras."""

from motores.guardas import validar_sql, verificar_cifras

PERMITIDOS = frozenset({"DWH_PROCOLOMBIA_SNOWFLAKE.SILVER"})


def test_validador_acepta_select_y_fuerza_limit() -> None:
    v = validar_sql(
        "SELECT DESC_PAIS, SUM(VLR_USD_EXPORTACION_FOB) F "
        "FROM DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.FACT_EXPORTACIONES_SL GROUP BY 1;",
        PERMITIDOS,
        5000,
    )
    assert v.ok and "LIMIT 5000" in v.sql and not v.sql.rstrip().endswith(";")


def test_validador_respeta_limit_existente_y_with() -> None:
    v = validar_sql("WITH a AS (SELECT 1 X) SELECT * FROM a LIMIT 10", PERMITIDOS, 5000)
    assert v.ok and v.sql.count("LIMIT") == 1


def test_validador_rechaza_escrituras_y_multisentencia() -> None:
    assert not validar_sql("DELETE FROM DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.X", PERMITIDOS, 100).ok
    assert not validar_sql("SELECT 1; SELECT 2", PERMITIDOS, 100).ok
    assert not validar_sql("SELECT * FROM OTRA_DB.PUBLIC.TABLA", PERMITIDOS, 100).ok


def test_verificador_aprueba_cifras_del_resultado() -> None:
    filas = [["Estados Unidos", 4211591218.59], ["China", 1250000000.0]]
    texto = "Estados Unidos lideró con 4.211.591.218,59 USD FOB, seguido de China con 1.250.000.000."
    assert verificar_cifras(texto, filas, 2).ok


def test_verificador_detecta_cifra_huerfana() -> None:
    filas = [["Café", 1000.5]]
    res = verificar_cifras("El café sumó 999.999 dólares en 2024.", filas, 1)
    assert not res.ok and any("999" in h for h in res.huerfanas)


def test_verificador_tolera_redondeos_y_ordinales() -> None:
    filas = [["Antioquia", 1234567.891]]
    texto = "Los 10 principales: Antioquia registró 1.234.567,89 dólares."
    assert verificar_cifras(texto, filas, 1).ok
