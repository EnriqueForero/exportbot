-- ============================================================================
-- ExportBot 2.0 · Telemetría — DDL EXACTO que espera backend/snowflake_/ejecutor.py
-- Destino por defecto: BD_EXPORTBOT.TELEMETRIA (cámbielo junto con la variable
-- SF_ESQUEMA_TELEMETRIA). Las columnas de CHAT_LOG coinciden 1:1 con el INSERT.
-- ============================================================================
CREATE DATABASE IF NOT EXISTS BD_EXPORTBOT;
CREATE SCHEMA IF NOT EXISTS BD_EXPORTBOT.TELEMETRIA;
USE SCHEMA BD_EXPORTBOT.TELEMETRIA;

CREATE TABLE IF NOT EXISTS CHAT_LOG (
  ID                   VARCHAR(64)   NOT NULL,
  TS                   TIMESTAMP_LTZ NOT NULL,
  SESSION_ID           VARCHAR(64),
  PREGUNTA             VARCHAR(2000),
  SQL_GENERADA         VARCHAR(4000),
  SQL_VALIDADA         BOOLEAN,
  EXITO                BOOLEAN,
  N_FILAS              NUMBER,
  LATENCIA_ANALYST_MS  NUMBER,
  LATENCIA_SQL_MS      NUMBER,
  LATENCIA_TOTAL_MS    NUMBER,
  PROVEEDOR_REDACCION  VARCHAR(64),
  MODELO_REDACCION     VARCHAR(128),
  CIFRAS_VERIFICADAS   BOOLEAN,
  INTENTOS             NUMBER,
  ERROR                VARCHAR(1000),
  VERSION_APP          VARCHAR(16),
  VERSION_SEMANTICA    VARCHAR(120)
) COMMENT = 'Una fila por pregunta procesada por ExportBot';

CREATE TABLE IF NOT EXISTS EVENTOS_APP (
  TS          TIMESTAMP_LTZ NOT NULL,
  SESSION_ID  VARCHAR(64),
  EVENTO      VARCHAR(64),
  DETALLES    VARIANT,
  VERSION_APP VARCHAR(16)
) COMMENT = 'Eventos de uso: arranques, descargas Excel/PPTX, accesos a métricas';

CREATE TABLE IF NOT EXISTS FEEDBACK (
  TS           TIMESTAMP_LTZ NOT NULL,
  CHAT_LOG_ID  VARCHAR(64),
  UTIL         BOOLEAN,
  COMENTARIO   VARCHAR(1000)
) COMMENT = 'Pulgar arriba/abajo de los usuarios sobre cada respuesta';

-- Permisos del rol de servicio (escritura SOLO aquí + lectura para /metricas)
GRANT USAGE ON DATABASE BD_EXPORTBOT TO ROLE R_EXPORTBOT_APP;
GRANT USAGE ON SCHEMA BD_EXPORTBOT.TELEMETRIA TO ROLE R_EXPORTBOT_APP;
GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA BD_EXPORTBOT.TELEMETRIA TO ROLE R_EXPORTBOT_APP;
GRANT INSERT, SELECT ON FUTURE TABLES IN SCHEMA BD_EXPORTBOT.TELEMETRIA TO ROLE R_EXPORTBOT_APP;
