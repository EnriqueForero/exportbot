# Diccionario de datos — `FACT_EXPORTACIONES_SL`

**Objeto:** `DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.FACT_EXPORTACIONES_SL`
**Tipo:** Tabla de hechos (fact) en modelo estrella
**Filas:** ~20.649.942
**Grano:** Un registro por declaración/línea de exportación, asociado a un mes (`WK_MES`), país destino, posición arancelaria, exportador, medio de transporte, etc.
**Cobertura temporal:** `WK_MES` de `200601` a `202604` (formato `YYYYMM`).

> **Nota importante (cambio de modelo).** El diccionario antiguo describía una tabla **plana/denormalizada** (con columnas como *País destino*, *Sector*, *Cadena*, *Año* ya resueltas en texto). La tabla actual en la capa **SILVER** es un **hecho normalizado**: contiene **claves foráneas** `WK_*` (numéricas) que se resuelven mediante `JOIN` contra tablas de dimensión `DIM_*_SL`, más las **métricas** `VLR_*`. Para reproducir las variables del diccionario antiguo hay que unir el hecho con sus dimensiones. Al final se incluye una **tabla de equivalencias**.

---

## 1. Columnas de la tabla de hechos

### 1.1 Métricas (medidas numéricas)

| Columna | Tipo | Definición | Unidad | Agregación |
|---|---|---|---|---|
| `VLR_USD_EXPORTACION_FOB` | NUMBER(18,2) | Valor exportado FOB (*Free On Board*). Es la métrica principal de valor. | USD | SUM |
| `VLR_USD_AGREGADO` | NUMBER(18,2) | Valor agregado en USD asociado a la operación. | USD | SUM |
| `VLR_USD_FLETES` | NUMBER(18,2) | Valor de fletes en USD. | USD | SUM |
| `VLR_USD_SEGUROS` | NUMBER(18,2) | Valor de seguros en USD. | USD | SUM |
| `VLR_USD_OTROS` | NUMBER(18,2) | Otros valores en USD asociados a la operación. | USD | SUM |
| `VLR_CANTIDAD` | NUMBER(18,2) | Cantidad exportada en la unidad comercial declarada (ver `WK_UNIDAD_COMERCIAL`). | Unidad comercial | SUM |
| `VLR_PESO_NETO_KG` | NUMBER(18,2) | Peso neto de la mercancía. | Kilogramos | SUM |
| `VLR_PESO_BRUTO_KG` | NUMBER(18,2) | Peso bruto de la mercancía. | Kilogramos | SUM |

### 1.2 Claves foráneas (dimensiones) y su join

| Columna (FK) | Tipo | Dimensión destino | Clave de join | Atributo descriptivo principal |
|---|---|---|---|---|
| `WK_MES` | NUMBER | `DIM_FECHA_SL` | `WK_MES` | Mes en formato `YYYYMM`. Ver §2.1 |
| `WK_PAIS_RECEPTOR` | NUMBER | `DIM_PAIS_SL` | `WK_PAIS` | `DESC_PAIS` (país destino) |
| `WK_DEPARTAMENTO_ORIGEN` | NUMBER | `DIM_DEPARTAMENTO_SL` | `WK_DEPARTAMENTO` | `DEPARTAMENTO` (departamento de origen) |
| `WK_DEPARTAMENTO_PROCEDENCIA` | NUMBER | `DIM_DEPARTAMENTO_SL` | `WK_DEPARTAMENTO` | `DEPARTAMENTO` (departamento de procedencia) |
| `WK_POSICION` | NUMBER | `DIM_ARANCEL_SL` | `WK_POSICION` | `ID_POSICION` / `DESC_POSICION` (arancel 10 dígitos) |
| `WK_MEDIO_TRANSPORTE` | NUMBER | `DIM_MEDIO_TRANSPORTE_SL` | `WK_MEDIO_TRANSPORTE` | `DESCRIPCION_MEDIO_TRANSPORTE` |
| `WK_MEDIO_TRANSPORTE_LOGISTICA` | NUMBER | `DIM_MEDIO_TRANSPORTE_SL` | `WK_MEDIO_TRANSPORTE` | `DESCRIPCION_MEDIO_TRANSPORTE` (medio logístico) |
| `WK_ADUANA` | NUMBER | `DIM_ADUANA_SL` | `WK_ADUANA` | `DESCRIPCION_ADUANA` |
| `WK_CIUDAD_SALIDA` | NUMBER | `DIM_CIUDAD_SL` | `WK_CIUDAD` | `DESC_CIUDAD` (ciudad de salida) |
| `WK_CUENTA_EXPORTADOR` | NUMBER | `DIM_CUENTA_SL` | `WK_CUENTA` | `RAZON_SOCIAL`, `NUMERO_IDENTIFICACION` (NIT) del exportador |
| `WK_CUENTA_DECLARANTE` | NUMBER | `DIM_CUENTA_SL` | `WK_CUENTA` | `RAZON_SOCIAL`, `NUMERO_IDENTIFICACION` (NIT) del declarante |
| `WK_UNIDAD_COMERCIAL` | NUMBER | (catálogo de unidades) | — | Unidad de medida de `VLR_CANTIDAD` (11 valores). |

### 1.3 Columnas descriptivas del importador (en el propio hecho)

| Columna | Tipo | Definición |
|---|---|---|
| `DESC_RAZON_IMPORTADOR` | TEXT(250) | Razón social del importador (país destino). |
| `DESC_DIRECCION_IMPORTADOR` | TEXT(250) | Dirección del importador. |
| `DESC_CIUDAD_IMPORTADOR` | TEXT(80) | Ciudad del importador. |
| `RAZN_EXP` | TEXT(250) | Razón social del exportador (texto tal como fue declarado). |

### 1.4 Códigos de la declaración (catálogos DIAN)

| Columna | Tipo | Definición | # valores |
|---|---|---|---|
| `CER_ORI3` | NUMBER | Código de certificado de origen. | 8 |
| `FORPAGO3` | NUMBER | Código de forma de pago. | 2 |
| `REGIMEN3` | NUMBER | Código de régimen aduanero. | 6 |

### 1.5 Columnas técnicas / auditoría

| Columna | Tipo | Definición |
|---|---|---|
| `ID` | NUMBER | Identificador técnico del registro. |
| `WK_FECHA_CREACION` | NUMBER | Fecha de creación del registro en bodega (clave `YYYYMMDD`). |
| `WK_FECHA_ACTUALIZACION` | NUMBER | Fecha de última actualización en bodega (clave `YYYYMMDD`). |

---

## 2. Dimensiones y vocabularios controlados

### 2.1 `DIM_FECHA_SL` (tiempo)
Join: `FACT.WK_MES = DIM_FECHA_SL.WK_MES`. `WK_MES` está en formato `YYYYMM`.
Atributos útiles: `WK_ANIO` (año), `DESC_MES_SP` (nombre mes), `WK_TRIMESTRE`, `WK_SEMESTRE`, `DESC_TRIMESTRE_ANIO`, `DESC_SEMESTRE_ANIO`, `DESC_PERIODO_PRESIDENCIAL`, `DESC_PRESIDENTE`, `DESC_MES_FISCAL`.
> El **año** se obtiene con `FLOOR(WK_MES/100)` o vía `DIM_FECHA_SL.WK_ANIO`.

### 2.2 `DIM_PAIS_SL` (país destino)
Join: `FACT.WK_PAIS_RECEPTOR = DIM_PAIS_SL.WK_PAIS`.

| Atributo | Definición | Valores (dominio) |
|---|---|---|
| `DESC_PAIS` | Nombre del país destino. | ~483 países / zonas francas |
| `COD_PAIS_ALFA_2` / `COD_PAIS_ALFA_3` | Código ISO alfa-2 / alfa-3. | — |
| `CONTINENTE_DANE_DIAN` | Continente destino. | América, Antártica, Asia, Europa, No Declarados, Oceanía, Zonas Francas Colombia, África |
| `HUB__C` | HUB comercial (agrupación de oficinas ProColombia). | Alianza Pacífico, Asia, Europa, Latinoamérica, Norteamérica, Otros |
| `OFICINA_COMERCIAL` | Oficina comercial que gestiona el país. | Alemania, Argentina, Brasil, Canadá, Caribe, Chile, China, Colombia, Costa Rica, Ecuador, España, Estados Unidos de América, Federación de Rusia, Francia, Guatemala, India, Indonesia, Japón, México, Otros, Perú, Reino Unido, República de Corea, Singapur |
| `ACUERDO` | Acuerdo comercial vigente con el país. | ALADI, ALADI;Alianza Pacífico, ALADI;Alianza Pacífico;CAN, ALADI;CAN, ALADI;Mercosur, Canadá, CARICOM, Corea, Costa Rica, EFTA, Estados Unidos, No Aplica, Triángulo Norte, Unión Europea |
| `REGION_COMUN`, `REGION_OMT`, `REGION_INVERSION` | Distintos niveles de agrupación regional. | (varios) |

### 2.3 `DIM_DEPARTAMENTO_SL` (departamento de origen / procedencia)
Join: `FACT.WK_DEPARTAMENTO_ORIGEN = DIM_DEPARTAMENTO_SL.WK_DEPARTAMENTO`.
`DEPARTAMENTO` — 32 departamentos de Colombia + `NULL`/desconocido:
Amazonas, Antioquia, Arauca, Atlántico, Bogotá, Bolívar, Boyacá, Caldas, Caquetá, Casanare, Cauca, Cesar, Chocó, Córdoba, Cundinamarca, Guainía, Guaviare, Huila, La Guajira, Magdalena, Meta, Nariño, Norte de Santander, Putumayo, Quindío, Risaralda, San Andrés y Providencia, Santander, Sucre, Tolima, Valle del Cauca, Vaupés, Vichada.

### 2.4 `DIM_ARANCEL_SL` (posición arancelaria → cadena / sector / tipo)
Join: `FACT.WK_POSICION = DIM_ARANCEL_SL.WK_POSICION`.
Esta dimensión es el puente hacia la sectorización de ProColombia.

| Atributo | Definición | Valores |
|---|---|---|
| `ID_POSICION` | Código arancelario de 10 dígitos. | — |
| `DESC_POSICION` | Descripción de la posición arancelaria. | texto |
| `TIPO` | Tipo minero/no minero. | Mineras, No Mineras |
| `CADENA_PRODUCTIVA` | Cadena productiva. | Agroalimentos, Industrias 4.0, Metalmecánica y Otras Industrias, Mineras, Otros, Químicos y Ciencias de la Vida, Sistema Moda |
| `CADENA_FRIO` | Requiere cadena de frío. | Si, No, No Definido |
| `ECONOMIA_NARANJA` | Pertenencia a economía naranja. | Inclusión Total, No Aplica |
| `WK_SECTOR` | FK a `DIM_SECTOR_SL` (`WK_SECTOR`). | — |
| `WK_SUBSECTOR_ARANCEL` | FK a `DIM_ARANCEL_SUBSECTOR_SL` (`WK_SUBSECTOR_ARANCEL`). | — |
| `WK_CIIU`, `WK_CPC`, `WK_CUCI`, `WK_CUODE` | Correspondencias con otras nomenclaturas. | — |

### 2.5 `DIM_SECTOR_SL` (sector) — join encadenado vía arancel
Join: `DIM_ARANCEL_SL.WK_SECTOR = DIM_SECTOR_SL.WK_SECTOR`.
`DESC_SECTOR` — sector productivo. `CADENA_PRODUCTIVA` y `APUESTA_HABILITANTE` como atributos adicionales.
> Es una dimensión **corporativa compartida** (~150 valores para todas las líneas de ProColombia: exportaciones, turismo, inversión). Para exportaciones filtre por los sectores de bienes (ej.: Café, Banano, Flores y plantas vivas, Cárnico, Cosméticos y productos de aseo, Metalmecánica, Textiles y confecciones, Petróleo y sus derivados, Carbón, Ferroníquel, etc.).

### 2.6 `DIM_ARANCEL_SUBSECTOR_SL` (subsector) — join encadenado vía arancel
Join: `DIM_ARANCEL_SL.WK_SUBSECTOR_ARANCEL = DIM_ARANCEL_SUBSECTOR_SL.WK_SUBSECTOR_ARANCEL`.
`DESC_SUBSECTOR_ARANCEL` — subsector del bien exportado.

### 2.7 `DIM_MEDIO_TRANSPORTE_SL`
Join: `FACT.WK_MEDIO_TRANSPORTE = DIM_MEDIO_TRANSPORTE_SL.WK_MEDIO_TRANSPORTE`.
`DESCRIPCION_MEDIO_TRANSPORTE`: Aéreo, Cabotaje, Correo, Ferroviario, Fluvial, Marítimo, Multimodal, No Aplica, No Definido, Otras Vías, Terrestre, Tubería.

### 2.8 `DIM_ADUANA_SL`
Join: `FACT.WK_ADUANA = DIM_ADUANA_SL.WK_ADUANA`. `DESCRIPCION_ADUANA` — aduana de trámite (63 valores).

### 2.9 `DIM_CIUDAD_SL`
Join: `FACT.WK_CIUDAD_SALIDA = DIM_CIUDAD_SL.WK_CIUDAD`. `DESC_CIUDAD` — ciudad de salida; incluye `CODIGO_DANE`, `DEPARTAMENTO_DIVIPOLA`, `PDET`, `ZOMAC`.

### 2.10 `DIM_CUENTA_SL` (empresa exportadora / declarante)
Join: `FACT.WK_CUENTA_EXPORTADOR = DIM_CUENTA_SL.WK_CUENTA`.

| Atributo | Definición | Valores |
|---|---|---|
| `RAZON_SOCIAL` | Nombre de la empresa. | texto |
| `NUMERO_IDENTIFICACION` | NIT del exportador. | texto |
| `TAMANO_EMPRESA` | Tamaño de la empresa. | Micro, Pequeña, Mediana, Grande, Desconocido |
| `SECTOR_ESTRELLA` | Sector que más exporta la empresa (variable "estrella"). | ver dominio de sector |
| `SUBSECTOR_ESTRELLA` | Subsector que más exporta la empresa. | ver dominio de subsector |
| `CADENA_ESTRELLA` | Cadena que más exporta la empresa. | ver dominio de cadena |
| `TIPO_ESTRELLA` | Tipo (minero/no minero) que más exporta. | Mineras, No Mineras |
| `DEPARTAMENTO_ESTRELLA` | Departamento del que más exporta la empresa. | ver dominio de departamento |
| `TIPO_CUENTA`, `ACTIVIDAD`, `CIIU` | Clasificación de la cuenta. | — |

> Las variables **"estrella"** del diccionario antiguo (`DPTO MÁS EXPORTA`, `CADENA*`, `SECTOR*`, `SUBSECTOR*`, `TIPO*`) **ya no se calculan sobre el hecho**: viven precalculadas en `DIM_CUENTA_SL` a nivel de empresa (NIT).

---

## 3. Equivalencia con el diccionario antiguo (tabla plana → modelo estrella)

| Variable antigua | Cómo obtenerla ahora |
|---|---|
| VALOR (USD FOB) | `SUM(FACT.VLR_USD_EXPORTACION_FOB)` |
| AÑO | `FLOOR(FACT.WK_MES/100)` o `DIM_FECHA_SL.WK_ANIO` |
| País destino | `DIM_PAIS_SL.DESC_PAIS` vía `WK_PAIS_RECEPTOR` |
| Continente | `DIM_PAIS_SL.CONTINENTE_DANE_DIAN` |
| Zona geográfica | `DIM_PAIS_SL.REGION_COMUN` / `REGION_OMT` |
| HUB | `DIM_PAIS_SL.HUB__C` |
| TLC'S / Tipo de acuerdo | `DIM_PAIS_SL.ACUERDO` |
| Departamento de origen | `DIM_DEPARTAMENTO_SL.DEPARTAMENTO` vía `WK_DEPARTAMENTO_ORIGEN` |
| Posición arancelaria | `DIM_ARANCEL_SL.ID_POSICION` vía `WK_POSICION` |
| Descripción posición | `DIM_ARANCEL_SL.DESC_POSICION` |
| Cadena | `DIM_ARANCEL_SL.CADENA_PRODUCTIVA` |
| Cadena frío | `DIM_ARANCEL_SL.CADENA_FRIO` |
| Economía naranja | `DIM_ARANCEL_SL.ECONOMIA_NARANJA` |
| Tipo (minera/no minera) | `DIM_ARANCEL_SL.TIPO` |
| Sector | `DIM_SECTOR_SL.DESC_SECTOR` (arancel → sector) |
| Subsector | `DIM_ARANCEL_SUBSECTOR_SL.DESC_SUBSECTOR_ARANCEL` |
| Medio de transporte | `DIM_MEDIO_TRANSPORTE_SL.DESCRIPCION_MEDIO_TRANSPORTE` |
| Nit exportador | `DIM_CUENTA_SL.NUMERO_IDENTIFICACION` vía `WK_CUENTA_EXPORTADOR` |
| Razón social | `DIM_CUENTA_SL.RAZON_SOCIAL` |
| DPTO MÁS EXPORTA (estrella) | `DIM_CUENTA_SL.DEPARTAMENTO_ESTRELLA` |
| CADENA* / SECTOR* / SUBSECTOR* / TIPO* | `DIM_CUENTA_SL.CADENA_ESTRELLA` / `SECTOR_ESTRELLA` / `SUBSECTOR_ESTRELLA` / `TIPO_ESTRELLA` |

---

## 4. Consulta de referencia (totalmente desnormalizada)

```sql
SELECT
    FLOOR(f.WK_MES/100)                    AS ANIO,
    f.WK_MES                               AS PERIODO_YYYYMM,
    p.DESC_PAIS                            AS PAIS_DESTINO,
    p.CONTINENTE_DANE_DIAN                 AS CONTINENTE,
    p.HUB__C                               AS HUB,
    p.ACUERDO                              AS ACUERDO_COMERCIAL,
    d.DEPARTAMENTO                         AS DEPARTAMENTO_ORIGEN,
    a.ID_POSICION                          AS POSICION_ARANCELARIA,
    a.DESC_POSICION                        AS DESC_POSICION,
    a.CADENA_PRODUCTIVA                    AS CADENA,
    a.TIPO                                 AS TIPO_MINERO,
    s.DESC_SECTOR                          AS SECTOR,
    ss.DESC_SUBSECTOR_ARANCEL              AS SUBSECTOR,
    mt.DESCRIPCION_MEDIO_TRANSPORTE        AS MEDIO_TRANSPORTE,
    c.RAZON_SOCIAL                         AS EXPORTADOR,
    c.NUMERO_IDENTIFICACION                AS NIT_EXPORTADOR,
    c.TAMANO_EMPRESA                       AS TAMANO_EMPRESA,
    SUM(f.VLR_USD_EXPORTACION_FOB)         AS TOTAL_USD_FOB,
    SUM(f.VLR_PESO_NETO_KG)                AS TOTAL_KG_NETO
FROM DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.FACT_EXPORTACIONES_SL      f
LEFT JOIN DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_PAIS_SL           p  ON f.WK_PAIS_RECEPTOR       = p.WK_PAIS
LEFT JOIN DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_DEPARTAMENTO_SL   d  ON f.WK_DEPARTAMENTO_ORIGEN = d.WK_DEPARTAMENTO
LEFT JOIN DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_ARANCEL_SL        a  ON f.WK_POSICION            = a.WK_POSICION
LEFT JOIN DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_SECTOR_SL         s  ON a.WK_SECTOR              = s.WK_SECTOR
LEFT JOIN DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_ARANCEL_SUBSECTOR_SL ss ON a.WK_SUBSECTOR_ARANCEL = ss.WK_SUBSECTOR_ARANCEL
LEFT JOIN DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_MEDIO_TRANSPORTE_SL mt ON f.WK_MEDIO_TRANSPORTE   = mt.WK_MEDIO_TRANSPORTE
LEFT JOIN DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.DIM_CUENTA_SL         c  ON f.WK_CUENTA_EXPORTADOR   = c.WK_CUENTA
WHERE f.WK_MES > 0
GROUP BY ALL;
```

---

## 5. Recomendaciones para el modelo semántico (NL → SQL)

1. **Definir la tabla base como el hecho** con las dimensiones como `relationships` (join por las claves `WK_*` indicadas en §1.2). Esto permite que Cortex Analyst resuelva nombres en texto sin exponer las claves.
2. **Medidas (`metrics`/`facts`):** `VLR_USD_EXPORTACION_FOB` (métrica principal, "valor exportado"/"exportaciones en USD"), `VLR_PESO_NETO_KG`, `VLR_PESO_BRUTO_KG`, `VLR_CANTIDAD`, `VLR_USD_FLETES`, `VLR_USD_SEGUROS`.
3. **Dimensión tiempo:** exponer `ANIO = FLOOR(WK_MES/100)` y `PERIODO = WK_MES` como columnas calculadas; agregar sinónimos "año", "mes", "periodo".
4. **Sinónimos** clave: país destino → {país, destino, mercado}; `VLR_USD_EXPORTACION_FOB` → {valor exportado, exportaciones, FOB, USD}; sector/cadena/subsector como filtros categóricos con los dominios de §2.
5. **Filtros de calidad:** `WK_MES > 0` (excluye registros sin fecha) y opcionalmente excluir `DESC_PAIS` en 'No Declarados'.
6. **Cuidado con dobles conteos:** hay dos departamentos (`ORIGEN` vs `PROCEDENCIA`) y dos medios de transporte (`_TRANSPORTE` vs `_LOGISTICA`); use el de "origen"/"transporte" salvo indicación contraria. Las variables "estrella" viven en `DIM_CUENTA_SL` (nivel empresa), no mezclarlas con la desagregación por operación.
