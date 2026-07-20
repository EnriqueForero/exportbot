-- ============================================================================
-- ExportBot 2.0 · Vistas del panel /metricas (las consumen routers/metricas.py
-- y la página MetricasPage; NO cambie los nombres de columna sin cambiar ambos).
-- ============================================================================
USE SCHEMA BD_EXPORTBOT.TELEMETRIA;

CREATE OR REPLACE VIEW V_CONSULTAS_DIARIAS AS
SELECT
  DATE_TRUNC('day', TS)::DATE      AS DIA,
  COUNT(*)                          AS CONSULTAS,
  COUNT_IF(EXITO)                   AS EXITOSAS,
  ROUND(AVG(LATENCIA_TOTAL_MS))     AS LATENCIA_PROM_MS
FROM CHAT_LOG
GROUP BY 1;

CREATE OR REPLACE VIEW V_PREGUNTAS_TOP AS
SELECT
  LOWER(TRIM(PREGUNTA))             AS PREGUNTA_NORM,
  COUNT(*)                          AS VECES,
  COUNT_IF(EXITO)                   AS EXITOSAS
FROM CHAT_LOG
GROUP BY 1;

GRANT SELECT ON ALL VIEWS IN SCHEMA BD_EXPORTBOT.TELEMETRIA TO ROLE R_EXPORTBOT_APP;
