# ExportBot 2.0 · ProColombia

Chatbot institucional que responde preguntas en lenguaje natural sobre las
**exportaciones de bienes de Colombia** (2006-01 → 2026-04) consultando Snowflake.
La SQL la genera **Cortex Analyst** sobre la vista semántica `SV_EXPORTACIONES`;
la app valida (solo lectura), ejecuta, redacta bajo contrato, **verifica cada
cifra contra el resultado** y audita todo en telemetría.

## Arranque rápido
1. **Snowflake** (una vez): ejecute `sql/01_seguridad_roles.sql`,
   `sql/02_telemetria_ddl.sql`, `sql/03_vistas_metricas.sql` y cree la vista
   semántica (Snowsight, o `semantic/crear_semantic_view.sql`, o VÍA B YAML en
   stage con `semantic/subir_yaml_a_stage.sql`).
2. **Local**: copie `.env.example` → `.env`, complete credenciales y corra
   `pip install -r backend/requirements.txt && (cd backend && uvicorn main:app --reload)`.
   El ZIP de release ya trae `frontend/dist` compilado; para desarrollo de UI:
   `cd frontend && npm install && npm run dev`.
3. **Colab efímero**: suba la carpeta a Drive (`ProColombia/exportbot`), cree los
   Secrets y ejecute `notebooks/Lanzar_App_Colab_Cloudflare.ipynb`.
4. **Railway**: repositorio → New Project; el `Dockerfile` y `railway.toml` hacen
   el resto. Variables = las de `.env.example` con `ARRANQUE_ESTRICTO=true`.

## Estructura
- `backend/` FastAPI (config, snowflake_, motores, orquestador, routers, exportadores, tests)
- `frontend/` React 18 + Vite + TS (chat con SSE, /metricas con token) · `dist/` en el release
- `semantic/` vista semántica del usuario + modelo enriquecido + suite dorada
- `sql/` roles, telemetría y vistas de métricas · `eval/` harness de exactitud
- `notebooks/` Lanzar (Colab+Cloudflare) y Publicar (GitHub) ya configurados
- `docs/` plan, estado del proyecto, runbook, decisiones, modelo semántico, diccionario

Documentación de entrada: **docs/ESTADO_DEL_PROYECTO.md** (qué está hecho y qué falta).
