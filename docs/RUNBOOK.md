# RUNBOOK · ExportBot 2.0 (operación paso a paso)

## 1. Preparación en Snowflake (una sola vez, 30–45 min)
1. `sql/01_seguridad_roles.sql` — crea `SVC_EXPORTBOT` (TYPE=SERVICE) y
   `R_EXPORTBOT_APP` con SELECT sobre SILVER + `SNOWFLAKE.CORTEX_USER`.
2. `sql/02_telemetria_ddl.sql` — `BD_EXPORTBOT.TELEMETRIA` (CHAT_LOG/EVENTOS_APP/FEEDBACK).
3. `sql/03_vistas_metricas.sql` — vistas del panel.
4. **Vista semántica** (elija UNA vía):
   - **A (recomendada)**: Snowsight → AI & ML → Cortex Analyst → Semantic Views →
     importar `semantic/SV_EXPORTACIONES.sv.yaml` o el enriquecido; o ejecutar
     `semantic/crear_semantic_view.sql` (plantilla: valide sintaxis).
   - **B**: `semantic/subir_yaml_a_stage.sql` + PUT de
     `modelo_exportaciones_analyst.yaml`; use `SF_SEMANTIC_MODEL_FILE`.
5. GRANT del final de cada script al rol de la app.

## 2. Credenciales del servicio (elija UNA)
- **PAT (simple)**: Snowsight → Admin → Users → SVC_EXPORTBOT → *Programmatic
  access tokens* → Generate (caducidad ≤ 90 días). Variable: `SF_PAT`.
- **Llaves RSA (rotación sin caída)**:
  `openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_key.p8` (+frase);
  `openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub`;
  `ALTER USER SVC_EXPORTBOT SET RSA_PUBLIC_KEY='MIIBIj...'` (la 2 en `RSA_PUBLIC_KEY_2`).
  Variables: `SF_PRIVATE_KEY_B64_1` = `base64 -w0 rsa_key.p8`, y la frase.
  **Rotación**: nueva llave → `RSA_PUBLIC_KEY_2` → mover env a `_1` cuando aplique.

## 3. Correr efímero desde Colab (demo)
1. Suba la carpeta del ZIP a Drive: `MiUnidad/ProColombia/exportbot` (trae `dist/` y
   `package.json` en la raíz: son los marcadores que las plantillas v3 buscan; la
   carpeta puede colgar directamente en esa ruta o un nivel más adentro).
2. Secrets de Colab (🔑): `SF_ACCOUNT`, `SF_USER`, `SF_PAT` (o llaves), `SF_ROLE`,
   `SF_WAREHOUSE`, `SF_SEMANTIC_VIEW` (o `SF_SEMANTIC_MODEL_FILE`),
   `SF_ESQUEMA_TELEMETRIA`, `ADMIN_TOKEN` y llaves LLM opcionales.
3. Ejecute `notebooks/Lanzar_App_Colab_Cloudflare.ipynb` (A → B → Pasos 1-3).
   Con `dist/` presente tarda ~1-3 min y verifica `/api/salud` en la URL pública.
4. Cierre la sesión al terminar: el enlace muere (es una demo, no hosting).

## 4. Desplegar en Railway (permanente)
1. Publique con `notebooks/Publicar_GitHub.ipynb` (gates pytest+ruff, manifiesto,
   PR a `main`).
2. railway.app → New Project → Deploy from GitHub → `EnriqueForero/exportbot`.
3. Variables: TODAS las de `.env.example` (mínimo cuenta+auth+semántica+telemetría+
   `ADMIN_TOKEN`) y `ARRANQUE_ESTRICTO=true`.
4. El `Dockerfile` compila el frontend y arranca Uvicorn; healthcheck `/api/salud`.
5. Smoke test: `/api/salud` = "ok", una pregunta dorada, descarga Excel, `/metricas`.

## 5. Calidad continua
- **Antes de cada release**: `pytest` + `ruff` (los gates del publicador ya lo
  imponen) y `python eval/evaluar.py` ≥ 90 %.
- **Semanal**: panel `/metricas` → preguntas fallidas y 👎 → convertir en
  verified queries o sinónimos (`docs/MODELO_SEMANTICO.md`).
- **Costos**: `SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY;`
  y el consumo del warehouse `APPS_WH` (QUERY_TAG = 'EXPORTBOT').

## 6. Incidentes rápidos
- `/api/salud` degradado → lea `problemas_configuracion` (nombra la variable).
- Analyst HTTP 4xx → PAT vencido/rol sin `CORTEX_USER`/vista sin GRANT.
- "Esquema fuera de la lista permitida" → añada `ESQUEMAS_PERMITIDOS` o corrija la VQ.
- Muchas respuestas "plantilla" → revise `CIFRAS_VERIFICADAS=false` en CHAT_LOG:
  ajuste el prompt del redactor o el verificador (formatos).
