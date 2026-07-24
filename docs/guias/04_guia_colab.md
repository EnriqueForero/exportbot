# 04 · Guía Google Colab — ExportBot 2.0.0
*Todo lo que ocurre en Colab (y los 3 pendientes de Snowflake que Colab necesita). Railway va en el documento 05. 2026-07-23.*

**Prerrequisito:** suba `exportbot_v2.0.0.zip` a Drive, descomprímalo y apunte la carpeta (§3). El rc1 ya trae: telemetría v2, middleware HTTP, `claude-sonnet-4-6` por defecto, casing MAYÚSCULAS corregido en el modelo y en las preguntas doradas, y el notebook preconfigurado.

---

## §0 · Pendientes de Snowflake que desbloquean Colab (15 min, una sola vez)

### 0.1 Otorgarse el rol para la prueba de mínimo privilegio
El error `Requested role 'R_EXPORTBOT_APP' is not assigned` es esperado: el rol solo está en `SVC_EXPORTBOT`. Ejecute:

```sql
USE ROLE SECURITYADMIN;
SET MI_USUARIO = CURRENT_USER();
GRANT ROLE R_EXPORTBOT_APP TO USER IDENTIFIER($MI_USUARIO);

USE ROLE R_EXPORTBOT_APP; USE WAREHOUSE APPS_WH;
INSERT INTO DB_EXPORTBOT.TELEMETRY.UI_EVENT (EVENT_TYPE, EVENT_DETAIL, ENVIRONMENT)
  VALUES ('prueba_manual', 'verificación de permisos §5', 'setup');
SELECT * FROM DB_EXPORTBOT.TELEMETRY.UI_EVENT ORDER BY EVENT_TS DESC LIMIT 3;   -- debe mostrar la fila
DELETE FROM DB_EXPORTBOT.TELEMETRY.UI_EVENT;                                    -- DEBE FALLAR (Insufficient privileges)
```

Si el `DELETE` **no** falla, sobran permisos: revise los GRANT del esquema TELEMETRY antes de seguir.

### 0.2 Credenciales del servicio: RSA (el PAT queda descartado)
Los usuarios `TYPE=SERVICE` solo pueden generar/usar PAT bajo una network policy, y Colab/Railway no tienen IP fija — abrir `0.0.0.0/0` anularía el control. Vía institucional: **par de llaves RSA** (el backend ya trae failover llave 1→2).

En su computador (no en Colab):

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_exportbot_1.p8 -nocrypt
openssl rsa -in rsa_exportbot_1.p8 -pubout -out rsa_exportbot_1.pub
```

En Snowsight (la pública va SIN cabeceras `BEGIN/END` y en una sola línea):

```sql
USE ROLE SECURITYADMIN;
ALTER USER SVC_EXPORTBOT SET RSA_PUBLIC_KEY='MIIBIjANBgkqhkiG9w0BAQ...';
DESC USER SVC_EXPORTBOT;   -- verifique que RSA_PUBLIC_KEY_FP quedó poblado (SHA256:...)
```

Prepare el secreto (una sola línea Base64 del PEM privado completo):

```bash
base64 -w0 rsa_exportbot_1.p8    # copie la salida → Secret SF_PRIVATE_KEY_B64_1
```

Guarde `rsa_exportbot_1.p8` donde guardan secretos del equipo (no en Drive compartido, no en el repo). Rotación futura: mismo proceso hacia `RSA_PUBLIC_KEY_2` + `SF_PRIVATE_KEY_B64_2`, sin downtime.

### 0.3 Verified queries: confirmar cuántas hay realmente
Su export del 23-07 trae **8** VQ; su narración dice **12** (G01–G12). En Snowsight → AI & ML → Cortex Analyst → `SV_EXPORTACIONES` → pestaña *Verified Queries*: cuente. Si las 12 G no están, cárguelas antes del eval (§6): evaluar contra una vista distinta a la que cree tener invalida el resultado.

---

## §1 · Secrets de Colab (🔑, una sola vez)

Mínimo para operar (Notebook → 🔑 → *Add new secret*, active el acceso del notebook):

- `SF_ACCOUNT` = identificador de la cuenta (el mismo que usa hoy para conectarse)
- `SF_USER` = `SVC_EXPORTBOT`
- `SF_ROLE` = `R_EXPORTBOT_APP`
- `SF_WAREHOUSE` = `APPS_WH`
- `SF_PRIVATE_KEY_B64_1` = la línea Base64 de §0.2

Opcionales: `SF_PRIVATE_KEY_B64_2` (rotación), `ADMIN_TOKEN` (si quiere abrir `/metricas` en la demo), llaves LLM externas (`GEMINI_API_KEY`, …) solo si va a comparar proveedores.

**Ya NO van en Secrets** (el notebook rc1 los fija como variables no sensibles en la Celda A): `SF_SEMANTIC_VIEW`, `SF_ESQUEMA_TELEMETRIA`, `SF_CORTEX_MODELO`, `ENTORNO_APP=colab`.

## §2 · Nada más que configurar
La Celda A del notebook `notebooks/Lanzar_App_Colab_Cloudflare.ipynb` ya apunta a `DB_EXPORTBOT.TELEMETRY`, `SV_EXPORTACIONES` y `claude-sonnet-4-6`. Solo verifique `RUTA_DRIVE` (dónde quedó la carpeta descomprimida).

## §3 · Lanzar
Ejecute las celdas en orden. El pipeline copia a disco local, sanea lockfiles, usa el `dist/` precompilado (sin Node ni build), levanta Uvicorn y verifica la URL pública de Cloudflare **desde afuera** hasta recibir HTTP 200. Verifique en la salida: `GET /api/salud` → `"estado": "ok"`, `"auth_snowflake": "keypair"`, `"entorno": "colab"`, `"telemetria": true`.

## §4 · Humo funcional (2 preguntas)
En la URL pública pregunte: *"¿Cuánto exportó Colombia en 2024?"* y *"Top 5 países destino en 2025"*. Debe ver etapas SSE (analyst → validación → ejecución → redacción) y una respuesta con cifras. Descargue un Excel de la segunda.

## §5 · Humo de telemetría v2 (en Snowsight, con su usuario)

```sql
-- (a) El middleware registró los requests:
SELECT EVENT_TS, METHOD, ENDPOINT, RESPONSE_STATUS, RESPONSE_TIME_MS, ENVIRONMENT, USER_ID
FROM DB_EXPORTBOT.TELEMETRY.EVENT_LOG ORDER BY EVENT_TS DESC LIMIT 10;

-- (b) El rastro completo pregunta→SQL→respuesta quedó guardado:
SELECT TS, PREGUNTA, LEFT(RESPUESTA, 80) AS RESPUESTA, RESPUESTA_DEGRADADA,
       CIFRAS_VERIFICADAS, LATENCIA_REDACCION_MS, VERSION_APP, ENVIRONMENT
FROM DB_EXPORTBOT.TELEMETRY.CHAT_LOG ORDER BY TS DESC LIMIT 5;

-- (c) Regresión del bug b2: APP_VERSION debe decir '2.0.0', jamás '':
SELECT EVENT_TS, EVENT_TYPE, EVENT_DETAIL, APP_VERSION
FROM DB_EXPORTBOT.TELEMETRY.UI_EVENT ORDER BY EVENT_TS DESC LIMIT 5;

-- (d) La descarga quedó ligada a su chat:
SELECT EVENT_TS, DOWNLOAD_TYPE, FILE_NAME, N_ROWS, CHAT_LOG_ID
FROM DB_EXPORTBOT.TELEMETRY.DOWNLOAD_EVENT ORDER BY EVENT_TS DESC LIMIT 5;
```

Criterio de éxito: (a)–(d) devuelven filas coherentes, `ENVIRONMENT='colab'`, `RESPUESTA` no viene vacía y (c) trae la versión real.

## §6 · El gate que decide: exactitud ≥ 90 %
En una celda nueva del notebook (con la app ya corriendo):

```python
!cd /content/exportbot_local && python eval/evaluar.py --url http://127.0.0.1:8000
```

(La ruta local exacta la imprime la Celda B al copiar el proyecto.) El script corre las 12 doradas comparando resultados contra la SQL de referencia — ahora con los literales en MAYÚSCULAS, de modo que un fallo es un fallo real del modelo, no del arnés. Si sale < 90 %: anote qué preguntas fallaron y con qué SQL; la corrección casi siempre es una verified query nueva o una regla adicional en `custom_instructions`, no código.

## §7 · Qué pegarme de vuelta
- Resultado de §0.1 (el `DELETE` falló: sí/no) y §0.3 (número real de VQ en Snowsight).
- La salida completa de §5 (a)–(d) y el porcentaje de §6 con el detalle de fallos si los hay.
- Con eso ajusto lo que haga falta y pasamos al documento 05 (Railway) con `ARRANQUE_ESTRICTO=true`.
