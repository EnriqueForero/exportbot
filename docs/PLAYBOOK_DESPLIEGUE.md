# PLAYBOOK DE DESPLIEGUE · ExportBot 2.0
**De cero a Railway, con prueba previa en Colab+Cloudflare.**
Versión 2.0.0b2 · 2026-07-19 · GIC ProColombia

Cada fase termina en un **CHECKPOINT verificable**: no avance sin cumplirlo. Donde
dice **[Prompt SI]** tiene un texto listo para pegarle a **Snowflake Intelligence**
(su IA con acceso a la cuenta); debajo va siempre el **SQL de respaldo** por si
prefiere un worksheet. Anote cada valor obtenido en el §F0 (su "hoja de valores").

---

## F0 · Hoja de valores (llénela a medida que avanza)

- `SF_ACCOUNT` = ______________ (formato ORG-CUENTA; sale en F1)
- `SF_USER` = ______________ (usuario de servicio; F2)
- Autenticación elegida: ☐ `SF_PAT` = ______  ·  ☐ llaves (`SF_PRIVATE_KEY_B64_1` + frase)
- `SF_ROLE` = ______________ · `SF_WAREHOUSE` = APPS_WH
- `SF_DATABASE` = DWH_PROCOLOMBIA_SNOWFLAKE · `SF_SCHEMA` = SILVER
- `SF_SEMANTIC_VIEW` = DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.SV_EXPORTACIONES (F4)
- `SF_ESQUEMA_TELEMETRIA` = BD_EXPORTBOT.TELEMETRIA (F5)
- `ADMIN_TOKEN` = ______________ (invéntelo: 24+ caracteres aleatorios)
- `GITHUB_TOKEN` (solo para publicar) = ______________

---

## F1 · Descubrimiento de la cuenta (10 min)

**1.1 Identificador de cuenta y región.**
**[Prompt SI]** «Ejecuta `SELECT CURRENT_ORGANIZATION_NAME() AS ORG,
CURRENT_ACCOUNT_NAME() AS CUENTA, CURRENT_REGION() AS REGION;` y devuélveme el
identificador en formato ORG-CUENTA y la región. Explica si esta cuenta usa el
formato de localizador antiguo.»
```sql
SELECT CURRENT_ORGANIZATION_NAME() AS ORG, CURRENT_ACCOUNT_NAME() AS CUENTA, CURRENT_REGION() AS REGION;
```
→ `SF_ACCOUNT = ORG-CUENTA` (con guion). El host REST será
`https://ORG-CUENTA.snowflakecomputing.com`.
Docs: https://docs.snowflake.com/en/user-guide/admin-account-identifier

**1.2 Cortex disponible (Analyst + COMPLETE).**
**[Prompt SI]** «Verifica si Cortex Analyst y la función SNOWFLAKE.CORTEX.COMPLETE
están habilitados en esta cuenta y región. Ejecuta
`SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2','Responde solo: OK');` y dime
qué modelos de COMPLETE están disponibles aquí.»
```sql
SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', 'Responde solo: OK');
```
Si el modelo no existe en su región: habilite inferencia entre regiones
(`ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';`) o cambie
`SF_CORTEX_MODELO` por uno disponible.
Docs: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cross-region-inference

**CHECKPOINT F1**: tiene `SF_ACCOUNT` anotado y COMPLETE respondió "OK".

---

## F2 · Usuario de servicio y rol (15 min)

Usted ya tiene usuarios de servicio; primero inventaríelos en vez de crear otro.

**2.1 Inventario.**
**[Prompt SI]** «Lista los usuarios de tipo SERVICE de la cuenta con
`SHOW USERS;` filtrando TYPE='SERVICE'. Para el que parezca de aplicaciones
analíticas, muéstrame `DESCRIBE USER <nombre>;` y dime: (a) si tiene
RSA_PUBLIC_KEY registrada, (b) su DEFAULT_ROLE y DEFAULT_WAREHOUSE, (c) qué
roles tiene concedidos según `SHOW GRANTS TO USER <nombre>;`.»

Decisión: si existe un usuario de servicio razonable, úselo como `SF_USER` y su
rol como base; si no, ejecute `sql/01_seguridad_roles.sql` del repo (crea
`SVC_EXPORTBOT` + `R_EXPORTBOT_APP`).

**2.2 Permisos mínimos del rol** (ejecute lo que falte; idempotente):
```sql
GRANT USAGE ON WAREHOUSE APPS_WH TO ROLE R_EXPORTBOT_APP;
GRANT USAGE ON DATABASE DWH_PROCOLOMBIA_SNOWFLAKE TO ROLE R_EXPORTBOT_APP;
GRANT USAGE ON SCHEMA DWH_PROCOLOMBIA_SNOWFLAKE.SILVER TO ROLE R_EXPORTBOT_APP;
GRANT SELECT ON ALL TABLES IN SCHEMA DWH_PROCOLOMBIA_SNOWFLAKE.SILVER TO ROLE R_EXPORTBOT_APP;
GRANT SELECT ON FUTURE TABLES IN SCHEMA DWH_PROCOLOMBIA_SNOWFLAKE.SILVER TO ROLE R_EXPORTBOT_APP;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE R_EXPORTBOT_APP;
GRANT ROLE R_EXPORTBOT_APP TO USER SVC_EXPORTBOT;
```
**[Prompt SI]** «Confirma con `SHOW GRANTS TO ROLE R_EXPORTBOT_APP;` que el rol
tiene SELECT sobre SILVER, USAGE del warehouse APPS_WH y el database role
SNOWFLAKE.CORTEX_USER. Señala cualquier permiso de escritura indebido.»

**CHECKPOINT F2**: `SF_USER` y `SF_ROLE` anotados; grants confirmados sin
escrituras fuera de telemetría.

---

## F3 · Credencial: PAT (camino corto) o llaves RSA (producción)

### Opción A — PAT (recomendada para la demo Colab; 5 min)
1. Snowsight → **Admin → Users & Roles →** su `SF_USER` → pestaña
   **Programmatic access tokens → Generate token**. Restrinja al rol
   `R_EXPORTBOT_APP`, caducidad ≤ 30 días. **Copie el secreto YA** (no vuelve a
   mostrarse) → `SF_PAT`.
2. Snowflake exige una **network policy activa** para autenticar con PAT. Si al
   usarlo recibe un error de política de red:
```sql
CREATE NETWORK POLICY IF NOT EXISTS NP_EXPORTBOT_ABIERTA ALLOWED_IP_LIST = ('0.0.0.0/0')
  COMMENT = 'Temporal para PAT de ExportBot; RESTRINGIR antes de producción';
ALTER USER SVC_EXPORTBOT SET NETWORK_POLICY = NP_EXPORTBOT_ABIERTA;
```
   Verdad incómoda: `0.0.0.0/0` es un candado de utilería. Sirve para la demo;
   para Railway restrinja a sus IP de egreso o quédese con llaves (Opción B).
   Docs: https://docs.snowflake.com/en/user-guide/programmatic-access-tokens

### Opción B — Par de llaves RSA (para Railway; 15 min)
```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes-256-cbc -inform PEM -out rsa_key.p8   # pide frase
openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
base64 -w0 rsa_key.p8 > rsa_key.p8.b64      # → SF_PRIVATE_KEY_B64_1
```
Registre la pública (contenido de `rsa_key.pub` SIN las líneas BEGIN/END):
```sql
ALTER USER SVC_EXPORTBOT SET RSA_PUBLIC_KEY = 'MIIBIjANBgkq...';
```
Verifique la huella (deben coincidir):
```sql
DESCRIBE USER SVC_EXPORTBOT;  -- fila RSA_PUBLIC_KEY_FP
```
```bash
openssl rsa -pubin -in rsa_key.pub -outform DER | openssl dgst -sha256 -binary | openssl enc -base64
```
Docs: https://docs.snowflake.com/en/user-guide/key-pair-auth
(Rotación sin caída: segunda llave en `RSA_PUBLIC_KEY_2` → `SF_PRIVATE_KEY_B64_2`.)

**CHECKPOINT F3**: tiene `SF_PAT` **o** `SF_PRIVATE_KEY_B64_1`+frase, y la huella
coincide (Opción B).

---

## F4 · Vista semántica (20 min)

**4.1 Crear.** Vía recomendada: Snowsight → **AI & ML → Cortex Analyst →
Semantic Views** → cree/importe usando `semantic/modelo_exportaciones_analyst.yaml`
del repo (es su YAML + sinónimos del diccionario + 7 reglas + 8 consultas
verificadas). Alternativas: `semantic/crear_semantic_view.sql` (plantilla DDL —
valide sintaxis) o VÍA B YAML-en-stage (`semantic/subir_yaml_a_stage.sql`).

**4.2 Permiso y humo.**
```sql
GRANT SELECT ON SEMANTIC VIEW DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.SV_EXPORTACIONES TO ROLE R_EXPORTBOT_APP;
```
**[Prompt SI]** «Sobre la vista semántica SV_EXPORTACIONES de SILVER: hazme la
pregunta "¿cuál fue el total exportado en USD FOB por año desde 2020?" usando
Cortex Analyst y muéstrame la SQL que genera. Confirma que filtra WK_MES > 0 y
que usa VLR_USD_EXPORTACION_FOB con SUM.»

**4.3 Humo REST desde SU máquina** (prueba la MISMA ruta que usará la app; con PAT):
```bash
curl -s -X POST "https://<SF_ACCOUNT>.snowflakecomputing.com/api/v2/cortex/analyst/message" \
  -H "Authorization: Bearer <SF_PAT>" \
  -H "X-Snowflake-Authorization-Token-Type: PROGRAMMATIC_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":[{"type":"text","text":"Total exportado por año desde 2023"}]}],
       "semantic_view":"DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.SV_EXPORTACIONES"}'
```
Esperado: HTTP 200 con un bloque `"type":"sql"`. 401 → PAT/política de red;
400 con "semantic" → nombre o GRANT de la vista.
Docs: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst

**CHECKPOINT F4**: el curl devuelve SQL. Este es EL checkpoint del proyecto: si
pasa, el 80 % del riesgo técnico murió aquí.

---

## F5 · Telemetría (10 min)

Ejecute `sql/02_telemetria_ddl.sql` y `sql/03_vistas_metricas.sql` (crean
`BD_EXPORTBOT.TELEMETRIA` con CHAT_LOG/EVENTOS_APP/FEEDBACK + vistas + GRANTs).
**[Prompt SI]** «Confirma que existen las tablas CHAT_LOG, EVENTOS_APP y FEEDBACK
y las vistas V_CONSULTAS_DIARIAS y V_PREGUNTAS_TOP en BD_EXPORTBOT.TELEMETRIA, y
que el rol R_EXPORTBOT_APP tiene INSERT+SELECT sobre las tablas y SELECT sobre
las vistas.»

**CHECKPOINT F5**: las 3 tablas y 2 vistas existen con permisos correctos.

---

## F6 · Prueba en Colab + Cloudflare (15–20 min)

**6.1 Drive.** Su carpeta actual `MiUnidad/ProColombia/exportbot` **sirve tal
cual** con los notebooks v3 (encuentran el proyecto por marcadores:
`pyproject.toml` + `backend/main.py` + `package.json` en raíz o `frontend/`).
Si descarga el ZIP **b2**, reemplace la carpeta: además trae `dist/` y
`package.json` en la raíz (contrato pleno de la plantilla).

**6.2 Secrets de Colab (🔑, "Notebook access" activado en cada uno):**
- Obligatorios: `SF_ACCOUNT`, `SF_USER`, `SF_ROLE`, `SF_WAREHOUSE`,
  `SF_SEMANTIC_VIEW`, `SF_ESQUEMA_TELEMETRIA`, `ADMIN_TOKEN` y **una** credencial
  (`SF_PAT`, o `SF_PRIVATE_KEY_B64_1` + `SF_PRIVATE_KEY_PASSPHRASE_1`).
- Opcionales: `SF_DATABASE`, `SF_SCHEMA`, `SF_CORTEX_MODELO`, llaves de LLM externos.

**6.3 Ejecute `notebooks/Lanzar_App_Colab_Cloudflare.ipynb` (v3)** en orden
A → B → Pasos. Señales de éxito por etapa:
- Traída: «✅ Proyecto listo … · 🎁 dist/ presente → se OMITEN Node, npm y build».
- Backend: «/api/salud» responde `estado: ok` (o `degradado` + QUÉ falta, por nombre).
- Túnel: URL `https://….trycloudflare.com`.

**6.4 Prueba de fuego en la URL pública:**
- Pregunte: «¿Cuánto exportó Colombia en USD FOB en 2024?» → tarjeta con chip
  **«Cifras verificadas contra el resultado»**, SQL visible y tabla.
- Descargue el Excel; abra `/metricas` e ingrese su `ADMIN_TOKEN`.

**6.5 Suite dorada desde el mismo Colab** (celda nueva al final):
```python
from google.colab import userdata; import os, subprocess
for k in ["SF_ACCOUNT","SF_USER","SF_PAT","SF_PRIVATE_KEY_B64_1","SF_PRIVATE_KEY_PASSPHRASE_1",
          "SF_ROLE","SF_WAREHOUSE","SF_SEMANTIC_VIEW","SF_ESQUEMA_TELEMETRIA"]:
    try:
        v = userdata.get(k)
        if v: os.environ[k] = v
    except Exception: pass
subprocess.run(["pip","install","-q","-r","backend/requirements.txt","PyYAML"], cwd="/content/app/exportbot")
print(subprocess.run(["python","eval/evaluar.py","--limite","8"], cwd="/content/app/exportbot",
                     capture_output=True, text=True).stdout)
```
**CHECKPOINT F6**: pregunta dorada respondida con cifras verificadas + eval con
exactitud reportada (meta del DoD: ≥ 90 %; si sale menos, afine sinónimos/VQs en
el YAML — `docs/MODELO_SEMANTICO.md` — y repita: es iteración normal, no fracaso).

---

## F7 · Publicar a GitHub (10 min)

1. Secret de Colab `GITHUB_TOKEN` (classic, scope `repo`).
2. Ejecute `notebooks/Publicar_GitHub.ipynb` (v3): gates = instala deps + pytest
   (y ruff si `GATE_COMPLETO=True`), verifica `RELEASE_MANIFEST.json` (bloquea si
   faltan archivos) y hace push a la rama `v2-lanzamiento` de
   `github.com/EnriqueForero/exportbot`.
3. En GitHub: abra el PR a `main` y confirme que el workflow `ci` pasa en verde.

**CHECKPOINT F7**: rama publicada + CI verde.

---

## F8 · Railway (20 min)

1. https://railway.app → **New Project → Deploy from GitHub repo** →
   `EnriqueForero/exportbot` (rama `main` tras el merge). El `Dockerfile` y
   `railway.toml` del repo hacen build (frontend+backend) y healthcheck
   `/api/salud`. Docs: https://docs.railway.com/guides/dockerfiles
2. **Variables** (Settings → Variables): las mismas de F6.2 **más**
   `ARRANQUE_ESTRICTO=true` (en producción, si falta algo, mejor que NO suba).
   Con llaves RSA pegue el Base64 completo en una línea.
3. Deploy → espere healthcheck verde → **Generate Domain**.
4. Smoke en el dominio: `/api/salud` = "ok"; 3 preguntas doradas; descarga Excel;
   `/metricas` con token; verifique en Snowflake que CHAT_LOG registró las filas:
```sql
SELECT TS, PREGUNTA, EXITO, CIFRAS_VERIFICADAS, LATENCIA_TOTAL_MS
FROM BD_EXPORTBOT.TELEMETRIA.CHAT_LOG ORDER BY TS DESC LIMIT 10;
```
5. Costos (semanal):
```sql
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY
ORDER BY START_TIME DESC LIMIT 20;   -- + consumo de APPS_WH con QUERY_TAG='EXPORTBOT'
```

**CHECKPOINT F8 (DoD de despliegue)**: dominio público estable, telemetría
escribiendo, exactitud dorada ≥ 90 % documentada en `eval/resultados/`.

---

## Solución de problemas (mapa error → causa → acción)

- «Se esperaba UN proyecto … 0» → notebooks viejos (v2) o Drive a medio
  sincronizar → use los v3; el error ahora LISTA subcarpetas y qué marcador falta.
- Analyst HTTP 401 → PAT vencido/mal copiado o política de red → F3.
- Analyst HTTP 400 «semantic…» → nombre de vista o GRANT SELECT → F4.2.
- «Esquema fuera de la lista permitida» → la SQL tocó otro esquema → agregue
  `ESQUEMAS_PERMITIDOS` o corrija la consulta verificada que lo indujo.
- Muchas respuestas «plantilla» → cifras huérfanas: revise
  `CIFRAS_VERIFICADAS=false` en CHAT_LOG y ajuste sinónimos o el prompt.
- Railway healthcheck falla → vea logs: con `ARRANQUE_ESTRICTO=true` el mensaje
  nombra la variable exacta que falta.

---

## Anexo · FOR Enrique (lecciones de esta iteración, compacto)

1) **Enfoque**: ante el error fui a leer la FUNCIÓN que lanzó la excepción, no a
adivinar sobre Drive; el traceback ya decía qué línea juzgaba. 2) **Descartado**:
parchar a mano su Celda B "prohibida" sin versionarla — en su lugar, plantilla
v3 con diagnóstico A08 documentado, como usted mismo versiona (A07.1). 3)
**Conexión**: el fallo era un CONTRATO implícito (marcadores de proyecto) que
nadie había escrito; ahora vive en el mensaje de error y en este playbook. 4)
**Herramienta**: reproduje la función parchada contra 4 layouts sintéticos antes
de entregarla — 30 segundos de arnés evitan su tercera vuelta. 5) **Trade-off**:
arreglé el repo (conformar) Y el notebook (tolerar); solo uno habría dejado una
mina para el próximo proyecto. 6) **Error del camino**: `re.sub` interpretó los
`\n` de mi texto de reemplazo y rompió un f-string — reemplazos con lambda desde
ahora. 7) **Trampa futura**: cuando una plantilla dice "encuentra el proyecto",
pregunte SIEMPRE "¿por cuáles marcadores?" antes de empaquetar. 8) **Ojo
experto**: un mensaje de error que lista lo que SÍ vio (subcarpetas, pistas)
convierte un ticket de soporte en un autoservicio de 30 segundos. 9)
**Transferible**: los contratos implícitos entre artefactos (zip ↔ notebook ↔
backend) se prueban con fixtures sintéticos, igual que el código.
