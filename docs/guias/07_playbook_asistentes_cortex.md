# 07 · Playbook — Asistentes de datos con Snowflake Cortex Analyst
*Guía replicable del patrón ExportBot para cualquier base de datos del equipo GIC. Destila lo aprendido (incluidos los errores) para que el próximo proyecto tarde días, no semanas. 2026-07-24.*

---

## 1 · El patrón en una imagen

```
Usuario pregunta en español
        │
        ▼
┌─ Backend propio (FastAPI) ──────────────────────────────────┐
│  1. Cortex Analyst (REST + JWT) ──► genera SQL desde la     │
│     vista semántica                                          │
│  2. Guardas: ¿solo SELECT? ¿esquemas permitidos? + LIMIT     │
│  3. Ejecuta con rol de SOLO LECTURA (driver + keypair)       │
│  4. Redacta la prosa (Cortex COMPLETE u otro LLM)            │
│  5. Verifica cifra a cifra: si no cuadra → plantilla segura  │
│  6. Telemetría: pregunta→SQL→respuesta, todo queda escrito   │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
Respuesta con cifras respaldadas + tabla + descarga
```

**La decisión de arquitectura que lo define todo:** el LLM *propone*, su código *dispone*. Cortex Analyst solo genera SQL; la ejecución, los límites y la verificación viven en SU backend. Por eso el patrón puede prometer "ninguna cifra sin respaldo llega al usuario" — promesa que ningún chat directo con un LLM puede hacer. Corolario: no migre a APIs que orquestan por usted (Agents) mientras esa promesa sea el corazón del producto.

## 2 · Los cimientos: diccionario y casing real (antes de cualquier IA)

El 80 % de la exactitud se decide aquí, sin escribir código:
1. **Diccionario de datos**: cada columna con descripción, unidad, y — crítico — **valores de ejemplo copiados de la base real**. No "Antioquia" de memoria: `SELECT DISTINCT DEPARTAMENTO LIMIT 20` y copie lo que salga (`ANTIOQUIA`).
2. **La lección del casing**: un literal en Title Case contra una base en MAYÚSCULAS devuelve 0 filas *sin error*. Es el bug más silencioso del patrón: la consulta "funciona" y miente. Regla: todo literal en verified queries, custom_instructions, sample_values y preguntas de evaluación se copia de la base, jamás se escribe de memoria.
3. **Reglas de negocio explícitas**: filtros obligatorios (ej. `WK_MES > 0`), cómo se deriva el año, qué significa cada métrica. Van a `custom_instructions` de la vista semántica — 5 a 10 reglas, numeradas.

## 3 · Vista semántica: donde vive la exactitud

- Créela en **Snowsight → AI & ML → Cortex Analyst** (valida sintaxis contra su cuenta al guardar). Contenido: tablas del modelo estrella, relaciones, medidas con descripción, sinónimos por columna, `custom_instructions`, y **verified queries**.
- **Verified queries = su palanca #1 de calidad.** Cada VQ es un par pregunta↔SQL curado que ancla el comportamiento del modelo. Empiece con 8–12 que cubran los tipos de pregunta frecuentes (totales, top-N, series, filtros por dimensión). Cuando la evaluación falle en un tipo de pregunta, la corrección casi siempre es una VQ nueva, no código.
- Versione el YAML en el repositorio del proyecto **y** re-exporte desde Snowsight después de cada cambio hecho en la interfaz: "estado declarado ≠ estado persistido" — cuente las VQs en la pestaña, no en su memoria.
- Otorgue al rol de la app: `GRANT SELECT ON SEMANTIC VIEW <db>.<schema>.<SV> TO ROLE R_<APP>_APP;`

## 4 · Seguridad: la plantilla de 15 minutos

Reemplace `<APP>` y ejecute (SECURITYADMIN para roles/usuarios, ACCOUNTADMIN para grants):

```sql
USE ROLE SECURITYADMIN;
CREATE ROLE IF NOT EXISTS R_<APP>_APP COMMENT = 'Solo lectura para <APP>';
CREATE USER IF NOT EXISTS SVC_<APP>
  DEFAULT_ROLE = R_<APP>_APP  DEFAULT_WAREHOUSE = APPS_WH
  TYPE = SERVICE  COMMENT = 'Cuenta de servicio de <APP>';
GRANT ROLE R_<APP>_APP TO USER SVC_<APP>;
ALTER USER SVC_<APP> SET DEFAULT_SECONDARY_ROLES = ();   -- higiene desde el día 1

USE ROLE ACCOUNTADMIN;
GRANT USAGE ON WAREHOUSE APPS_WH TO ROLE R_<APP>_APP;
GRANT USAGE ON DATABASE <DB_DATOS> TO ROLE R_<APP>_APP;
GRANT USAGE ON SCHEMA <DB_DATOS>.<ESQUEMA> TO ROLE R_<APP>_APP;
GRANT SELECT ON ALL TABLES IN SCHEMA <DB_DATOS>.<ESQUEMA> TO ROLE R_<APP>_APP;
GRANT SELECT ON FUTURE TABLES IN SCHEMA <DB_DATOS>.<ESQUEMA> TO ROLE R_<APP>_APP;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE R_<APP>_APP;
```

**Los cinco mandamientos aprendidos con sangre:**
1. **Un usuario de servicio POR app.** La cuenta compartida acopla rotaciones, amplía el radio de explosión de una llave filtrada y — el argumento técnico definitivo — la API REST de Cortex Analyst opera con el **DEFAULT_ROLE del usuario del JWT** (no acepta rol en el cuerpo): con cuenta compartida, su asistente correría con el rol de otra app, y "arreglarlo" cambiando el default rompe a los demás.
2. **La dirección del GRANT importa**: `GRANT ROLE <rol_de_gestión> TO ROLE <rol_de_app>` hace que la app herede privilegios de gestor. Léalo dos veces antes de ejecutar.
3. **`DEFAULT_SECONDARY_ROLES = ()`** en usuarios de servicio: un rol otorgado por error no debe activarse solo.
4. **La prueba de mínimo privilegio se hace con `USE SECONDARY ROLES NONE;`** — en Snowsight, su usuario humano lleva sus roles de administrador activos en segundo plano y el DELETE "funciona", dándole un falso negativo. Sin ese `USE`, la prueba lo mide a usted, no al rol.
5. El éxito de la prueba es que el **DELETE falle**. Auditoría que la app puede borrar no es auditoría.

## 5 · Llaves RSA: el procedimiento a prueba de la confusión que ya vivimos

**Por qué RSA y no PAT:** los tokens programáticos de usuarios de servicio exigen una network policy, y los despliegues sin IP fija (Colab, Railway estándar) la vuelven inviable sin abrirla a todo internet — lo que anula su propósito.

**La confusión que causó nuestro incidente** (memorícela): Snowflake pide la llave **pública** "sin cabeceras, en una línea"; el secreto de la app lleva la **privada** como archivo **completo** codificado. Dos formatos opuestos para dos objetos parecidos. El procedimiento que la elimina:

```bash
# 1. Generar el par (una vez, en su máquina):
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_<app>_1.p8 -nocrypt
openssl rsa -in rsa_<app>_1.p8 -pubout -out rsa_<app>_1.pub

# 2. Secreto de la app (PRIVADA, archivo completo, una línea Base64):
base64 -w0 rsa_<app>_1.p8        # Windows: [Convert]::ToBase64String([IO.File]::ReadAllBytes("rsa_<app>_1.p8"))
```

```sql
-- 3. Registrar la PÚBLICA (sin cabeceras BEGIN/END, una línea):
ALTER USER SVC_<APP> SET RSA_PUBLIC_KEY='MIIBIjANBgkq...';
DESC USER SVC_<APP>;   -- RSA_PUBLIC_KEY_FP debe quedar poblada: ANÓTELA
```

**Las tres verificaciones que cierran el círculo:**
- `DESC USER` → `HAS_KEYPAIR = true` y huella anotada.
- La app arranca y su `/api/salud` muestra `llave_rsa: legible (SHA256:...)` **idéntica** a la anotada. Idénticas = la llave que firma es la registrada.
- `/api/salud` muestra `usuario_snowflake` = `SVC_<APP>`. **La lección del 401**: llave correcta + huella coincidente + "JWT token is invalid" = el token declara OTRA identidad (casi siempre un `SF_USER` equivocado en los secretos). La identidad efectiva debe ser visible en el endpoint de salud — cópielo en todo proyecto nuevo.

**Rotación sin downtime:** genere el par 2 → `RSA_PUBLIC_KEY_2` → secreto `..._B64_2` → cuando todo use la 2, retire la 1. Y **nunca configure el secreto de una llave 2 cuya pública no esté registrada**: el failover hacia ella solo fabrica 401.

## 6 · Telemetría: la caja negra estándar

Reutilice el DDL de ExportBot (`sql/02_telemetria_v2_ddl.sql`) cambiando `DB_EXPORTBOT` por `DB_<APP>`. El diseño que vale la pena copiar tal cual:

- **5 tablas**: `EVENT_LOG` (cada request HTTP), `CHAT_LOG` (una fila por pregunta con el rastro completo: pregunta, SQL, **respuesta entregada**, si hubo degradación, latencias por etapa), `UI_EVENT` (interfaz), `DOWNLOAD_EVENT` (ligada al chat origen), `FEEDBACK`.
- **4 columnas de identidad en TODAS**: `APP_NAME`, `APP_VERSION`, `ENVIRONMENT`, `USER_ID` (default 'anonymous'). Cuestan una línea el día 1 y una migración dolorosa el día 100. `ENVIRONMENT` es la que le permite ver dev y prod en la misma tabla sin mezclarlos.
- **`TIMESTAMP_LTZ` + `TIMEZONE='America/Bogota'` como parámetro de sesión de la conexión** — jamás `CONVERT_TIMEZONE` regado por las consultas.
- **Grants: INSERT + SELECT, nada más.** Fail-open en el código: si la telemetría falla, la app sigue; la auditoría no puede tumbar el servicio.
- Vistas de análisis encima (`V_USO_DIARIO`, `V_CALIDAD_RESPUESTAS`) — el panel consulta vistas, no tablas.

## 7 · Evaluación: el número que gobierna el "listo"

- **Preguntas doradas**: 10–12 preguntas reales con su SQL de referencia escrita a mano (casing real). El evaluador compara *resultados*, no texto.
- **DoD explícito**: ≥ 90 % antes de producción. Sin ese número, "ya casi funciona" se vuelve eterno.
- Cuando falle: mire QUÉ SQL generó vs la referencia. El arreglo es (en este orden): una verified query nueva → una regla de custom_instructions → un sinónimo → y solo al final, código.
- Todo subprocess de evaluación se lee con `returncode + stdout + stderr`. "No salió nada" casi siempre significa "el error está en el flujo que no imprimí".

## 8 · Panel de métricas y el token (gobierno de acceso)

- El panel consulta las vistas de telemetría vía backend, protegido con `ADMIN_TOKEN` (cabecera comparada con `compare_digest`; token vacío = panel cerrado, cerrado por defecto).
- **Por qué el token se queda aunque "no sea confidencial"**: (i) las *preguntas de los usuarios* son señal estratégica — qué mercados, productos y empresas investiga la entidad; (ii) la URL es pública (Cloudflare/Railway): sin token, cualquiera con el enlace lee y además martilla un endpoint que consume warehouse; (iii) el costo de un token fuerte es idéntico al de uno débil — ambos se copian y pegan — así que el token débil es riesgo gratis. Genere: `openssl rand -hex 32`, guárdelo en el gestor de contraseñas del equipo, compártalo por canal seguro.
- Qué mirar cada semana: `V_USO_DIARIO` (adopción), `V_CALIDAD_RESPUESTAS` (éxito, degradadas, feedback), y costos: `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY` + auto-suspend del warehouse.

## 9 · Despliegue por entornos

- **Regla**: mismos binarios, distinta severidad. Dev (Colab+Cloudflare): `ARRANQUE_ESTRICTO=false` — la app sube y declara qué falta en `/salud`. Prod (Railway): `ARRANQUE_ESTRICTO=true` — configuración incompleta o llave ilegible = el deploy muere gritando la causa.
- **Fail-fast de credenciales al arranque** (cópielo a todo proyecto): la app intenta cargar la llave al iniciar y publica veredicto + huella + identidad en `/salud`. Un secreto roto se descubre al desplegar, no en la primera consulta de un usuario.
- Variables por entorno: `ENTORNO_APP` (colab|railway) viaja a la telemetría; el resto (cuenta, usuario, llave, vista semántica, esquema de telemetría, modelo) idénticas.
- Los defaults de modelos LLM caducan en meses: variable de entorno con fecha de revisión, jamás constante en el código.

## 10 · Checklist replicable (imprímalo para el próximo proyecto)

**Snowflake (día 1):** diccionario con valores reales → plantilla de seguridad §4 → par RSA + pública registrada + huella anotada → DDL de telemetría → vista semántica con 8+ VQs → GRANT de la SV al rol → prueba mínimo privilegio con `SECONDARY ROLES NONE` (DELETE falla).
**Backend (día 2–3):** clonar el esqueleto ExportBot → cambiar config (app, esquemas, SV) → `/salud` con identidad y llave visibles → preguntas doradas propias.
**Validación (día 4):** lanzar en dev → salud en verde con huella idéntica → consulta real → telemetría con filas → eval ≥ 90 %.
**Producción (día 5):** variables + `ARRANQUE_ESTRICTO=true` → verificación post-deploy → panel con token fuerte → anuncio con 2 preguntas de ejemplo.

## 11 · Errores de guerra (síntoma → verdad)

- *"0 filas sin error"* → literal con casing de memoria. Copie de la base.
- *"Error interno" genérico en el primer uso* → secreto ilegible sin fail-fast. Valide credenciales al arranque.
- *401 con llave y huella correctas* → identidad equivocada en el token (SF_USER). Hágala visible en /salud.
- *DELETE que "funciona" en la prueba de privilegios* → secondary roles activos. `USE SECONDARY ROLES NONE`.
- *"Lo corrí y todo salió bien" y luego nada existe* → paso sin verificación observable. Todo paso termina en un SHOW/SELECT con resultado esperado.
- *La IA de la cuenta propone "corregir" hacia lo que existe* → ve estado, no contrato. Las decisiones de rumbo son del diseño del proyecto; a las IAs de cuenta, pídales SHOW y DESC.
- *Eval "no imprime nada"* → estaba en stderr. returncode + stdout + stderr, siempre.
- *Base con nombre casi igual (BD_ vs DB_)* → ejecute DDLs por archivo del repositorio versionado, y verifique con `SHOW DATABASES LIKE` al terminar.
