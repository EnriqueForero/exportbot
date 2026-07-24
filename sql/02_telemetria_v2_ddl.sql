-- ============================================================================
-- ExportBot 2.0 · TELEMETRÍA v2 — DB_EXPORTBOT.TELEMETRY
-- ----------------------------------------------------------------------------
-- Diseño: convención ProColombia 2026-05-13 (schema TELEMETRY, tablas en
-- inglés, EVENT_ID por UUID, VARIANT para extensibilidad — ver
-- modelo_potencialidad_etl-main/sql/06_create_telemetry_tables.sql) MEJORADA:
--   1. Se agrega APP_NAME/APP_VERSION/ENVIRONMENT en TODAS las tablas: el mismo
--      esquema sirve para futuras apps de la GIC sin tocar el DDL.
--   2. Se agrega USER_ID (default 'anonymous') en TODAS las tablas: cuando
--      exista registro de usuarios/SSO, no habrá migración.
--   3. CHAT_LOG guarda la RESPUESTA final entregada (requisito explícito:
--      pregunta → SQL → respuesta, el rastro completo).
--   4. Zona horaria resuelta de raíz: TIMESTAMP_LTZ guarda el instante
--      absoluto (UTC interno); la app fija TIMEZONE='America/Bogota' en la
--      sesión y las vistas convierten para presentación. Se elimina para
--      siempre el parche CONVERT_TIMEZONE('America/Los_Angeles', ...) que
--      arrastran registrar_evento (CITI) y Tres Ejes.
--   5. SIN cluster keys (diferencia deliberada frente al estándar): a este
--      volumen (miles de filas/día) el auto-clustering solo quema créditos.
--      Añadir CLUSTER BY (TO_DATE(EVENT_TS)) únicamente si una tabla supera
--      ~100M de filas. https://docs.snowflake.com/en/user-guide/tables-clustering-keys
--   6. Retro-compatibilidad: los INSERT del código b2 actual sobre CHAT_LOG y
--      FEEDBACK funcionan sin cambios (mismas columnas, tipos compatibles).
--      EVENTOS_APP desaparece: la reemplaza UI_EVENT (el código v2 la usará;
--      mientras tanto los log_evento del b2 fallan en silencio por diseño
--      fail-open — pérdida acotada y conocida durante la transición).
--
-- Ejecutar con un rol con permisos de creación (SYSADMIN o ACCOUNTADMIN).
-- Si prefiere otro nombre de base, reemplace DB_EXPORTBOT en todo el archivo
-- y ajuste la variable de entorno SF_ESQUEMA_TELEMETRIA en Railway/Colab:
--   SF_ESQUEMA_TELEMETRIA=DB_EXPORTBOT.TELEMETRY
-- ============================================================================

USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS DB_EXPORTBOT
  COMMENT = 'Base propia de ExportBot: telemetría y objetos de la aplicación (los datos de negocio viven en DWH_PROCOLOMBIA_SNOWFLAKE)';

CREATE SCHEMA IF NOT EXISTS DB_EXPORTBOT.TELEMETRY
  COMMENT = 'Eventos emitidos por la app sobre el comportamiento de los usuarios (convención ProColombia 2026-05-13)';

USE SCHEMA DB_EXPORTBOT.TELEMETRY;

-- ────────────────────────────────────────────────────────────────────────────
-- 1. EVENT_LOG — 1 fila por request HTTP al backend (middleware FastAPI).
--    Es la capa "todo lo que pasa": clics que llegan al API, accesos a
--    /metricas, descargas, errores 4xx/5xx, latencias.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS EVENT_LOG (
  EVENT_ID         VARCHAR(36)    DEFAULT UUID_STRING()      COMMENT 'UUID del evento',
  EVENT_TS         TIMESTAMP_LTZ  DEFAULT CURRENT_TIMESTAMP() COMMENT 'Instante absoluto (mostrar en Bogotá vía vistas)',
  APP_NAME         VARCHAR(50)    DEFAULT 'exportbot'        COMMENT 'Permite compartir el esquema entre apps',
  APP_VERSION      VARCHAR(16)                               COMMENT 'Contenido de VERSION en el release',
  ENVIRONMENT      VARCHAR(20)                               COMMENT 'railway | colab | dev',
  USER_ID          VARCHAR(200)   DEFAULT 'anonymous'        COMMENT 'Email cuando exista SSO; anonymous mientras tanto',
  SESSION_ID       VARCHAR(36)                               COMMENT 'UUID generado por el navegador (cabecera X-Session-Id)',
  CLIENT_IP        VARCHAR(45)                               COMMENT 'IPv4/IPv6 del cliente',
  USER_AGENT       VARCHAR(500)                              COMMENT 'Truncado a 500',
  METHOD           VARCHAR(10)                               COMMENT 'GET, POST, ...',
  ENDPOINT         VARCHAR(200)                               COMMENT 'p.ej. /api/chat',
  REQUEST_PAYLOAD  VARIANT                                    COMMENT 'Body JSON truncado (~16KB) — sin secretos',
  RESPONSE_STATUS  NUMBER(3,0)                                COMMENT '200, 401, 500, ...',
  RESPONSE_TIME_MS NUMBER(10,2)                               COMMENT 'Duración del request',
  CONSTRAINT PK_EVENT_LOG PRIMARY KEY (EVENT_ID)
) COMMENT = 'Log genérico de cada llamada HTTP al backend de ExportBot';

-- ────────────────────────────────────────────────────────────────────────────
-- 2. CHAT_LOG — 1 fila por pregunta procesada (la tabla de mayor valor).
--    Retro-compatible con el INSERT del b2 y AMPLIADA con: RESPUESTA final,
--    degradación a plantilla, latencia de redacción, USER_ID/ENVIRONMENT y
--    DETALLES (VARIANT) para crecer sin ALTER.
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS CHAT_LOG (
  ID                    VARCHAR(64)   NOT NULL                 COMMENT 'chat_id (UUID hex) generado por el orquestador',
  TS                    TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
  SESSION_ID            VARCHAR(64),
  USER_ID               VARCHAR(200)  DEFAULT 'anonymous',
  APP_NAME              VARCHAR(50)   DEFAULT 'exportbot',
  ENVIRONMENT           VARCHAR(20),
  PREGUNTA              VARCHAR(2000) COMMENT 'Texto del usuario (puede contener nombres/NIT: tratar como dato interno)',
  SQL_GENERADA          VARCHAR(8000) COMMENT 'SQL final ejecutada (validada, con LIMIT)',
  SQL_VALIDADA          BOOLEAN       COMMENT 'FALSE si el validador de solo lectura la rechazó',
  EXITO                 BOOLEAN,
  N_FILAS               NUMBER,
  RESPUESTA             VARCHAR(8000) COMMENT 'Texto final entregado al usuario (truncado a 8000)',
  RESPUESTA_DEGRADADA   BOOLEAN       COMMENT 'TRUE si la capa 5 forzó plantilla determinística',
  LATENCIA_ANALYST_MS   NUMBER,
  LATENCIA_SQL_MS       NUMBER,
  LATENCIA_REDACCION_MS NUMBER,
  LATENCIA_TOTAL_MS     NUMBER,
  PROVEEDOR_REDACCION   VARCHAR(64),
  MODELO_REDACCION      VARCHAR(128),
  CIFRAS_VERIFICADAS    BOOLEAN,
  INTENTOS              NUMBER        COMMENT '1 normal; 2 si hubo autocorrección de SQL',
  ERROR                 VARCHAR(1000),
  VERSION_APP           VARCHAR(16),
  VERSION_SEMANTICA     VARCHAR(200)  COMMENT 'Vista semántica o ruta del YAML usada en esa respuesta',
  DETALLES              VARIANT       COMMENT 'Extensión libre (nuevos campos sin ALTER)',
  CONSTRAINT PK_CHAT_LOG PRIMARY KEY (ID)
) COMMENT = 'Una fila por pregunta: rastro completo pregunta → SQL → respuesta';

-- ────────────────────────────────────────────────────────────────────────────
-- 3. UI_EVENT — eventos libres del frontend (clics, aperturas, selecciones).
--    Reemplaza a EVENTOS_APP. Mapeo con el estándar CITI de Nico:
--    EVENT_TYPE ≈ TIPO_EVENTO · EVENT_DETAIL ≈ DETALLE_EVENTO ·
--    EVENT_TARGET ≈ UNIDAD (ver vista de compatibilidad al final).
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS UI_EVENT (
  EVENT_ID     VARCHAR(36)   DEFAULT UUID_STRING(),
  EVENT_TS     TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
  APP_NAME     VARCHAR(50)   DEFAULT 'exportbot',
  APP_VERSION  VARCHAR(16),
  ENVIRONMENT  VARCHAR(20),
  USER_ID      VARCHAR(200)  DEFAULT 'anonymous',
  SESSION_ID   VARCHAR(36),
  EVENT_TYPE   VARCHAR(64)   NOT NULL COMMENT 'app_inicio | click | seleccion | vista_metricas | error_ui | ...',
  EVENT_DETAIL VARCHAR(200)           COMMENT 'Descripción corta del evento',
  EVENT_TARGET VARCHAR(200)           COMMENT 'Objeto del evento (botón, país, sector...) — equivale a UNIDAD',
  PAGE         VARCHAR(50)            COMMENT 'chat | metricas | ...',
  PAYLOAD      VARIANT                COMMENT 'JSON libre para nuevos eventos sin ALTER',
  CONSTRAINT PK_UI_EVENT PRIMARY KEY (EVENT_ID)
) COMMENT = 'Eventos de interfaz reportados por el frontend (flexible por diseño)';

-- ────────────────────────────────────────────────────────────────────────────
-- 4. DOWNLOAD_EVENT — descargas tipadas (Excel/PPTX), enlazadas a la pregunta
--    de origen (mejora sobre el estándar: trazabilidad descarga → chat).
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS DOWNLOAD_EVENT (
  EVENT_ID      VARCHAR(36)   DEFAULT UUID_STRING(),
  EVENT_TS      TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
  APP_NAME      VARCHAR(50)   DEFAULT 'exportbot',
  APP_VERSION   VARCHAR(16),
  ENVIRONMENT   VARCHAR(20),
  USER_ID       VARCHAR(200)  DEFAULT 'anonymous',
  SESSION_ID    VARCHAR(36),
  CHAT_LOG_ID   VARCHAR(64)            COMMENT 'ID de CHAT_LOG cuyo resultado se descargó',
  DOWNLOAD_TYPE VARCHAR(20)            COMMENT 'excel | pptx',
  FILE_NAME     VARCHAR(200),
  N_ROWS        NUMBER(10,0),
  N_COLS        NUMBER(5,0),
  DETAILS       VARIANT,
  CONSTRAINT PK_DOWNLOAD_EVENT PRIMARY KEY (EVENT_ID)
) COMMENT = 'Descargas de archivos generadas por la app, con vínculo a la consulta origen';

-- ────────────────────────────────────────────────────────────────────────────
-- 5. FEEDBACK — pulgar arriba/abajo por respuesta (retro-compatible con b2).
-- ────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS FEEDBACK (
  EVENT_ID    VARCHAR(36)   DEFAULT UUID_STRING(),
  TS          TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
  CHAT_LOG_ID VARCHAR(64),
  UTIL        BOOLEAN,
  COMENTARIO  VARCHAR(1000),
  USER_ID     VARCHAR(200)  DEFAULT 'anonymous',
  SESSION_ID  VARCHAR(36),
  APP_NAME    VARCHAR(50)   DEFAULT 'exportbot',
  CONSTRAINT PK_FEEDBACK PRIMARY KEY (EVENT_ID)
) COMMENT = 'Retroalimentación del usuario sobre cada respuesta (insumo directo de calidad)';

-- ============================================================================
-- VISTAS DEL PANEL /metricas
-- Las dos primeras conservan nombre y columnas del b2: el panel actual
-- funciona sin cambios apuntando SF_ESQUEMA_TELEMETRIA a este esquema.
-- Todas presentan el día en hora de Bogotá.
-- ============================================================================

CREATE OR REPLACE VIEW V_CONSULTAS_DIARIAS AS
SELECT
  DATE_TRUNC('day', CONVERT_TIMEZONE('America/Bogota', TS))::DATE AS DIA,
  COUNT(*)                      AS CONSULTAS,
  COUNT_IF(EXITO)               AS EXITOSAS,
  ROUND(AVG(LATENCIA_TOTAL_MS)) AS LATENCIA_PROM_MS
FROM CHAT_LOG
GROUP BY 1;

CREATE OR REPLACE VIEW V_PREGUNTAS_TOP AS
SELECT
  LOWER(TRIM(PREGUNTA)) AS PREGUNTA_NORM,
  COUNT(*)              AS VECES,
  COUNT_IF(EXITO)       AS EXITOSAS
FROM CHAT_LOG
GROUP BY 1;

-- Métricas de uso combinadas por día (estilo V_DAILY_USAGE_METRICS del estándar)
CREATE OR REPLACE VIEW V_USO_DIARIO AS
WITH http AS (
  SELECT DATE_TRUNC('day', CONVERT_TIMEZONE('America/Bogota', EVENT_TS))::DATE AS FECHA,
         COUNT(DISTINCT NULLIF(SESSION_ID, '')) AS SESIONES_UNICAS,
         COUNT(*)                               AS TOTAL_REQUESTS,
         ROUND(AVG(RESPONSE_TIME_MS), 2)        AS LATENCIA_PROM_MS,
         COUNT_IF(RESPONSE_STATUS >= 500)       AS ERRORES_5XX,
         COUNT_IF(RESPONSE_STATUS BETWEEN 400 AND 499) AS ERRORES_4XX
  FROM EVENT_LOG GROUP BY 1
), chats AS (
  SELECT DATE_TRUNC('day', CONVERT_TIMEZONE('America/Bogota', TS))::DATE AS FECHA,
         COUNT(*)                        AS PREGUNTAS,
         COUNT_IF(EXITO)                 AS PREGUNTAS_EXITOSAS,
         COUNT_IF(RESPUESTA_DEGRADADA)   AS RESPUESTAS_DEGRADADAS
  FROM CHAT_LOG GROUP BY 1
), descargas AS (
  SELECT DATE_TRUNC('day', CONVERT_TIMEZONE('America/Bogota', EVENT_TS))::DATE AS FECHA,
         COUNT(*)                          AS DESCARGAS,
         COUNT_IF(DOWNLOAD_TYPE = 'excel') AS DESCARGAS_EXCEL,
         COUNT_IF(DOWNLOAD_TYPE = 'pptx')  AS DESCARGAS_PPTX
  FROM DOWNLOAD_EVENT GROUP BY 1
)
SELECT COALESCE(h.FECHA, c.FECHA, d.FECHA) AS FECHA,
       COALESCE(h.SESIONES_UNICAS, 0)  AS SESIONES_UNICAS,
       COALESCE(h.TOTAL_REQUESTS, 0)   AS TOTAL_REQUESTS,
       COALESCE(h.LATENCIA_PROM_MS, 0) AS LATENCIA_PROM_MS,
       COALESCE(h.ERRORES_4XX, 0)      AS ERRORES_4XX,
       COALESCE(h.ERRORES_5XX, 0)      AS ERRORES_5XX,
       COALESCE(c.PREGUNTAS, 0)        AS PREGUNTAS,
       COALESCE(c.PREGUNTAS_EXITOSAS, 0)      AS PREGUNTAS_EXITOSAS,
       COALESCE(c.RESPUESTAS_DEGRADADAS, 0)   AS RESPUESTAS_DEGRADADAS,
       COALESCE(d.DESCARGAS, 0)        AS DESCARGAS,
       COALESCE(d.DESCARGAS_EXCEL, 0)  AS DESCARGAS_EXCEL,
       COALESCE(d.DESCARGAS_PPTX, 0)   AS DESCARGAS_PPTX
FROM http h
FULL OUTER JOIN chats c     ON h.FECHA = c.FECHA
FULL OUTER JOIN descargas d ON COALESCE(h.FECHA, c.FECHA) = d.FECHA
ORDER BY FECHA DESC;

-- Auditoría de calidad respuesta a respuesta (pregunta, SQL, respuesta, feedback)
CREATE OR REPLACE VIEW V_CALIDAD_RESPUESTAS AS
SELECT
  CONVERT_TIMEZONE('America/Bogota', c.TS) AS TS_BOGOTA,
  c.ID, c.USER_ID, c.SESSION_ID, c.PREGUNTA, c.SQL_GENERADA, c.RESPUESTA,
  c.EXITO, c.CIFRAS_VERIFICADAS, c.RESPUESTA_DEGRADADA, c.INTENTOS,
  c.PROVEEDOR_REDACCION, c.MODELO_REDACCION, c.VERSION_SEMANTICA,
  c.LATENCIA_TOTAL_MS, c.ERROR,
  f.UTIL AS FEEDBACK_UTIL, f.COMENTARIO AS FEEDBACK_COMENTARIO
FROM CHAT_LOG c
LEFT JOIN FEEDBACK f ON f.CHAT_LOG_ID = c.ID;

-- Compatibilidad con el estándar CITI (registrar_evento de Nico): permite que
-- los tableros del equipo que leen SEGUIMIENTO_EVENTOS hagan UNION con
-- ExportBot sin transformar nada.
CREATE OR REPLACE VIEW V_SEGUIMIENTO_EVENTOS_COMPAT AS
SELECT EVENT_TYPE                                   AS TIPO_EVENTO,
       EVENT_DETAIL                                 AS DETALLE_EVENTO,
       EVENT_TARGET                                 AS UNIDAD,
       EVENT_TYPE                                   AS TIPO_BOTON,
       CONVERT_TIMEZONE('America/Bogota', EVENT_TS) AS FECHA_HORA
FROM UI_EVENT
UNION ALL
SELECT 'Descarga', 'Descarga ' || COALESCE(DOWNLOAD_TYPE, ''), FILE_NAME,
       'Descarga ' || COALESCE(DOWNLOAD_TYPE, ''),
       CONVERT_TIMEZONE('America/Bogota', EVENT_TS)
FROM DOWNLOAD_EVENT;

-- ============================================================================
-- PERMISOS del rol de servicio (mínimo privilegio: escribe SOLO aquí)
-- Ajuste el nombre del rol si en su cuenta se llama distinto (p. ej. APP_EXPORTBOT).
-- ============================================================================
GRANT USAGE ON DATABASE DB_EXPORTBOT                    TO ROLE R_EXPORTBOT_APP;
GRANT USAGE ON SCHEMA  DB_EXPORTBOT.TELEMETRY           TO ROLE R_EXPORTBOT_APP;
GRANT INSERT, SELECT ON ALL TABLES    IN SCHEMA DB_EXPORTBOT.TELEMETRY TO ROLE R_EXPORTBOT_APP;
GRANT INSERT, SELECT ON FUTURE TABLES IN SCHEMA DB_EXPORTBOT.TELEMETRY TO ROLE R_EXPORTBOT_APP;
GRANT SELECT ON ALL VIEWS    IN SCHEMA DB_EXPORTBOT.TELEMETRY TO ROLE R_EXPORTBOT_APP;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA DB_EXPORTBOT.TELEMETRY TO ROLE R_EXPORTBOT_APP;

-- ============================================================================
-- OPCIONAL (recomendado) · Gobierno del dato
-- PREGUNTA y REQUEST_PAYLOAD pueden contener nombres de empresas o NIT: el
-- esquema debe quedar accesible SOLO al rol de la app y a los administradores
-- de la GIC. Time Travel corto para no pagar almacenamiento de histórico:
--   ALTER SCHEMA DB_EXPORTBOT.TELEMETRY SET DATA_RETENTION_TIME_IN_DAYS = 1;
-- Si definen una política de retención (p. ej. 24 meses), impleméntela con una
-- TASK mensual de DELETE por EVENT_TS — la dejo lista en el código v2 si la quieren.
-- ============================================================================
