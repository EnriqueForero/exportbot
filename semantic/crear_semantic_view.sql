-- ============================================================================
-- ExportBot 2.0 · Creación de la SEMANTIC VIEW en Snowflake (VÍA A — recomendada)
-- ⚠️ PLANTILLA: valide la sintaxis en su cuenta (la gramática de SEMANTIC VIEW
--    ha evolucionado). Alternativa equivalente y soportada por la app (VÍA B):
--    subir semantic/modelo_exportaciones_analyst.yaml a un stage y configurar
--    SF_SEMANTIC_MODEL_FILE (ver subir_yaml_a_stage.sql). La VÍA MÁS SIMPLE es
--    crear/editar la vista con el asistente de Snowsight (AI & ML → Cortex
--    Analyst → Semantic Views) importando el YAML.
-- Docs: https://docs.snowflake.com/en/user-guide/views-semantic/overview
-- ============================================================================
USE ROLE ACCOUNTADMIN;  -- o el rol propietario del esquema SILVER
USE DATABASE DWH_PROCOLOMBIA_SNOWFLAKE;
USE SCHEMA SILVER;

CREATE OR REPLACE SEMANTIC VIEW SV_EXPORTACIONES
  TABLES (
    F  AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.FACT_EXPORTACIONES_SL,
    P  AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_PAIS_SL              PRIMARY KEY (WK_PAIS),
    D  AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_DEPARTAMENTO_SL      PRIMARY KEY (WK_DEPARTAMENTO),
    A  AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_ARANCEL_SL           PRIMARY KEY (WK_POSICION),
    S  AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_SECTOR_SL            PRIMARY KEY (WK_SECTOR),
    SS AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_ARANCEL_SUBSECTOR_SL PRIMARY KEY (WK_SUBSECTOR_ARANCEL),
    MT AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_MEDIO_TRANSPORTE_SL  PRIMARY KEY (WK_MEDIO_TRANSPORTE),
    AD AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_ADUANA_SL            PRIMARY KEY (WK_ADUANA),
    C  AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_CIUDAD_SL            PRIMARY KEY (WK_CIUDAD),
    CU AS DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_CUENTA_SL            PRIMARY KEY (WK_CUENTA)
  )
  RELATIONSHIPS (
    F (WK_PAIS_RECEPTOR)       REFERENCES P,
    F (WK_DEPARTAMENTO_ORIGEN) REFERENCES D,
    F (WK_POSICION)            REFERENCES A,
    F (WK_MEDIO_TRANSPORTE)    REFERENCES MT,
    F (WK_ADUANA)              REFERENCES AD,
    F (WK_CIUDAD_SALIDA)       REFERENCES C,
    F (WK_CUENTA_EXPORTADOR)   REFERENCES CU,
    A (WK_SECTOR)              REFERENCES S,
    A (WK_SUBSECTOR_ARANCEL)   REFERENCES SS
  )
  FACTS (
    F.VLR_USD_FOB   AS VLR_USD_EXPORTACION_FOB COMMENT 'Valor FOB en USD (métrica principal)',
    F.VLR_PESO_NETO AS VLR_PESO_NETO_KG        COMMENT 'Peso neto (kg)',
    F.VLR_CANT      AS VLR_CANTIDAD            COMMENT 'Cantidad en unidad comercial'
  )
  DIMENSIONS (
    F.ANIO     AS FLOOR(WK_MES/100) WITH SYNONYMS ('año','vigencia') COMMENT 'Año calendario (de WK_MES YYYYMM)',
    F.PERIODO  AS WK_MES            WITH SYNONYMS ('mes','periodo','yyyymm'),
    P.PAIS     AS DESC_PAIS         WITH SYNONYMS ('país','destino','mercado'),
    P.CONTINENTE AS CONTINENTE_DANE_DIAN WITH SYNONYMS ('continente'),
    P.HUB      AS HUB__C            WITH SYNONYMS ('hub','hub comercial'),
    P.ACUERDO  AS ACUERDO           WITH SYNONYMS ('acuerdo comercial','tlc'),
    D.DEPARTAMENTO AS DEPARTAMENTO  WITH SYNONYMS ('departamento','departamento de origen'),
    A.POSICION AS ID_POSICION       WITH SYNONYMS ('posición arancelaria','subpartida'),
    A.TIPO_MINERO AS TIPO           WITH SYNONYMS ('minero o no minero'),
    A.CADENA   AS CADENA_PRODUCTIVA WITH SYNONYMS ('cadena','cadena productiva'),
    S.SECTOR   AS DESC_SECTOR       WITH SYNONYMS ('sector'),
    SS.SUBSECTOR AS DESC_SUBSECTOR_ARANCEL WITH SYNONYMS ('subsector'),
    MT.MEDIO   AS DESCRIPCION_MEDIO_TRANSPORTE WITH SYNONYMS ('medio de transporte','vía'),
    AD.ADUANA  AS DESCRIPCION_ADUANA WITH SYNONYMS ('aduana'),
    C.CIUDAD_SALIDA AS DESC_CIUDAD  WITH SYNONYMS ('ciudad de salida'),
    CU.EXPORTADOR AS RAZON_SOCIAL   WITH SYNONYMS ('empresa','exportador'),
    CU.NIT     AS NUMERO_IDENTIFICACION WITH SYNONYMS ('nit'),
    CU.TAMANO  AS TAMANO_EMPRESA    WITH SYNONYMS ('tamaño de empresa')
  )
  METRICS (
    F.TOTAL_USD_FOB AS SUM(VLR_USD_EXPORTACION_FOB) COMMENT 'Suma del valor FOB en USD',
    F.TOTAL_KG_NETO AS SUM(VLR_PESO_NETO_KG)        COMMENT 'Suma del peso neto en kg'
  )
  COMMENT = 'Exportaciones de bienes de Colombia · grano mensual (WK_MES>0) · USD FOB';

-- Prueba rápida:
-- SELECT * FROM SEMANTIC_VIEW(SV_EXPORTACIONES METRICS TOTAL_USD_FOB DIMENSIONS ANIO) ORDER BY ANIO DESC;
