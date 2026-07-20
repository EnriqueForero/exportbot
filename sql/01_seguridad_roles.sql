-- ============================================================================
-- ExportBot 2.0 · Seguridad: usuario de servicio + rol de mínimo privilegio
-- Ejecutar con un rol administrador (SECURITYADMIN/ACCOUNTADMIN). Ajuste nombres.
-- Nota 2025-2026: Snowflake bloquea contraseñas single-factor para usuarios de
-- servicio; use PAT o par de llaves RSA (ver docs/RUNBOOK.md §2).
--   https://docs.snowflake.com/en/user-guide/key-pair-auth
--   https://docs.snowflake.com/en/user-guide/programmatic-access-tokens
-- ============================================================================
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS R_EXPORTBOT_APP COMMENT = 'Rol de solo lectura para ExportBot';

CREATE USER IF NOT EXISTS SVC_EXPORTBOT
  DEFAULT_ROLE = R_EXPORTBOT_APP
  DEFAULT_WAREHOUSE = APPS_WH
  TYPE = SERVICE                       -- usuario de servicio: sin contraseña interactiva
  COMMENT = 'Cuenta de servicio de ExportBot 2.0 (GIC)';
GRANT ROLE R_EXPORTBOT_APP TO USER SVC_EXPORTBOT;

-- (Llaves RSA) Registre la pública:  ALTER USER SVC_EXPORTBOT SET RSA_PUBLIC_KEY='MIIBIj...';
-- (Rotación)  segunda llave:         ALTER USER SVC_EXPORTBOT SET RSA_PUBLIC_KEY_2='MIIBIj...';
-- (PAT)       genérelo en Snowsight → Admin → Users → SVC_EXPORTBOT → Programmatic access tokens.

USE ROLE ACCOUNTADMIN;
-- Cómputo
GRANT USAGE ON WAREHOUSE APPS_WH TO ROLE R_EXPORTBOT_APP;
-- Lectura del modelo estrella (SOLO SELECT sobre SILVER)
GRANT USAGE ON DATABASE DWH_PROCOLOMBIA_SNOWFLAKE TO ROLE R_EXPORTBOT_APP;
GRANT USAGE ON SCHEMA DWH_PROCOLOMBIA_SNOWFLAKE.SILVER TO ROLE R_EXPORTBOT_APP;
GRANT SELECT ON ALL TABLES IN SCHEMA DWH_PROCOLOMBIA_SNOWFLAKE.SILVER TO ROLE R_EXPORTBOT_APP;
GRANT SELECT ON FUTURE TABLES IN SCHEMA DWH_PROCOLOMBIA_SNOWFLAKE.SILVER TO ROLE R_EXPORTBOT_APP;
-- Vista semántica (si usa VÍA A)
-- GRANT SELECT ON SEMANTIC VIEW DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.SV_EXPORTACIONES TO ROLE R_EXPORTBOT_APP;
-- Cortex (Analyst + COMPLETE)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE R_EXPORTBOT_APP;
-- Telemetría (escritura SOLO en su propio esquema; ver 02_telemetria_ddl.sql)
