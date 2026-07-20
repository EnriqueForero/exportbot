-- ============================================================================
-- ExportBot 2.0 · VÍA B — Modelo semántico como YAML en un stage
-- Úsela si prefiere gobernar el modelo como archivo (Git) en vez de objeto SQL.
-- La app lo consume con: SF_SEMANTIC_MODEL_FILE=@BD_EXPORTBOT.CONFIG.SEMANTICA/modelo_exportaciones_analyst.yaml
-- ============================================================================
CREATE DATABASE IF NOT EXISTS BD_EXPORTBOT;
CREATE SCHEMA IF NOT EXISTS BD_EXPORTBOT.CONFIG;
CREATE STAGE IF NOT EXISTS BD_EXPORTBOT.CONFIG.SEMANTICA
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Modelos semánticos YAML de ExportBot';

-- Desde SnowSQL / Snowsight (Upload) / driver, en la carpeta semantic/ del repo:
--   PUT file://modelo_exportaciones_analyst.yaml @BD_EXPORTBOT.CONFIG.SEMANTICA
--       AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
LS @BD_EXPORTBOT.CONFIG.SEMANTICA;

-- El rol de servicio necesita leer el stage:
--   GRANT USAGE ON DATABASE BD_EXPORTBOT TO ROLE R_EXPORTBOT_APP;
--   GRANT USAGE ON SCHEMA BD_EXPORTBOT.CONFIG TO ROLE R_EXPORTBOT_APP;
--   GRANT READ  ON STAGE BD_EXPORTBOT.CONFIG.SEMANTICA TO ROLE R_EXPORTBOT_APP;
