# RUNBOOK · ExportBot 2.0 (operación e incidentes)

Guía de operación en producción y desarrollo. Para la puesta en marcha inicial
paso a paso, use `docs/guias/06_manual_puesta_en_marcha.md` (fuente canónica).

## 1 · Preparación en Snowflake (una vez)
1. `sql/01_seguridad_roles.sql` — `SVC_EXPORTBOT` (TYPE=SERVICE) + `R_EXPORTBOT_APP`
   (solo lectura sobre SILVER + `SNOWFLAKE.CORTEX_USER`). Después:
   `ALTER USER SVC_EXPORTBOT SET DEFAULT_SECONDARY_ROLES = ();`
2. **Llaves RSA**: pública → `ALTER USER ... SET RSA_PUBLIC_KEY` (sin cabeceras);
   privada → secreto `SF_PRIVATE_KEY_B64_1` (`base64 -w0` del `.p8` completo).
   Verifique `DESC USER SVC_EXPORTBOT` → `RSA_PUBLIC_KEY_FP` poblada; ANÓTELA.
3. `sql/02_telemetria_v2_ddl.sql` — crea `DB_EXPORTBOT.TELEMETRY` (5 tablas +
   vistas + grants INSERT/SELECT). ⚠️ El DDL v1 (`BD_EXPORTBOT.TELEMETRIA`) es
   LEGADO (`sql/legado/`); no lo ejecute.
4. Vista semántica `SV_EXPORTACIONES` en Snowsight + verified queries +
   `GRANT SELECT ON SEMANTIC VIEW ... TO ROLE R_EXPORTBOT_APP;`
5. Prueba de mínimo privilegio (con `USE SECONDARY ROLES NONE;`): INSERT y
   SELECT pasan, **DELETE falla**.

## 2 · Desarrollo (Colab + Cloudflare)
`notebooks/Lanzar_App_Colab_Cloudflare.ipynb`. Secrets: los 5 de conexión.
Éxito = `/api/salud` con `estado:ok`, `usuario_snowflake:SVC_EXPORTBOT`,
`llave_rsa:legible(huella idéntica a la anotada)`, `entorno:colab`.

## 3 · Producción (Railway)
`docs/guias/05_guia_railway.md`. Claves: deploy desde GitHub, mismas credenciales,
`ENTORNO_APP=railway`, **`ARRANQUE_ESTRICTO=true`** (config incompleta o llave
ilegible = el deploy aborta declarando la causa), `ADMIN_TOKEN` fuerte
(`openssl rand -hex 32`).

## 4 · Señales de salud
- `/api/salud`: identidad + llave + problemas. Primera parada SIEMPRE.
- Log de arranque: `Telemetría activa hacia DB_EXPORTBOT.TELEMETRY`.
- Panel `/metricas` (token): uso diario, calidad, degradadas, feedback.
- Costos: `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY` + auto-suspend
  del warehouse.

## 5 · Incidentes conocidos (síntoma → causa → acción)
- **"Error interno" genérico en el chat** → (histórico, rc1) secreto de llave
  ilegible sin fail-fast → desde 2.0.0 imposible: `/api/salud` lo declara.
- **`MalformedFraming` / llave ilegible** → secreto en formato inesperado →
  desde 2.0.0 se aceptan PEM-b64, DER-b64 y PEM crudo; si aún ilegible, el
  mensaje de `/api/salud` dicta la corrección exacta.
- **401 `JWT token is invalid` con `llave_rsa: legible` y huella idéntica** →
  el token declara OTRA identidad → compare `usuario_snowflake` en `/api/salud`
  con el dueño de la llave; corrija el secreto `SF_USER`. Si el log alterna
  `llave=2`, existe un `SF_PRIVATE_KEY_B64_2` sin `RSA_PUBLIC_KEY_2` registrada:
  bórrelo o registre la pública 2.
- **La prueba de privilegios "permite" DELETE en Snowsight** → secondary roles
  del usuario humano activos → repita con `USE SECONDARY ROLES NONE;`.
- **`Database ... does not exist or not authorized`** → base inexistente en esa
  cuenta o rol sin visibilidad → `SHOW DATABASES LIKE '%EXPORTBOT%'` con rol
  admin; si solo existe `BD_EXPORTBOT` (v1), ejecute el DDL v2.
- **Publicador de GitHub bloquea por versiones incoherentes** → algún archivo de
  versión quedó atrás → las cuatro fuentes (VERSION, pyproject, package.json,
  frontend) deben ser idénticas; `pytest backend/tests/test_version_coherente.py`
  lo verifica.
- **Eval "no imprime nada"** → se leyó solo stdout → use returncode + stdout +
  stderr (comando correcto en el manual, Fase 6).
- **Colab "instalando" eterno** → lockfiles con espejo privado (histórico b1) →
  saneador automático en los notebooks.

## 6 · Rotación de llaves (6–12 meses, sin downtime)
Par 2 → `RSA_PUBLIC_KEY_2` → secreto `SF_PRIVATE_KEY_B64_2` → redeploy → cuando
todo firme con la 2, retire la 1. Nunca configure el secreto 2 sin registrar su
pública (fabrica 401 en el failover).

## 7 · Retiro del legado
`DROP DATABASE BD_EXPORTBOT;` **solo** tras confirmar filas reales en
`DB_EXPORTBOT.TELEMETRY` (manual, Fase 8.4).
