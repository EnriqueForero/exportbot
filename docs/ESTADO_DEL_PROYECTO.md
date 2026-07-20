# Estado del proyecto · ExportBot 2.0.0b1 — 2026-07-19

Mapa contra las fases del plan (`docs/PLAN_EXPORTBOT_2.md` §10). Verificado en esta
construcción: **18/18 pruebas**, `ruff` limpio, **build de producción** de Vite OK
(`frontend/dist` incluido en el ZIP), manifiesto SHA-256 generado.

## ✅ Hecho (esta entrega)
- **F0 · Fundaciones**: monorepo completo, `pyproject.toml`, `ruff` + isort first-party,
  pruebas, CI GitHub Actions, pre-commit, `.env.example`, `Dockerfile`, `railway.toml`,
  `RELEASE_MANIFEST.json` (74 archivos) compatible con su `Publicar_GitHub.ipynb`.
- **F1 · Capa semántica (código y archivos)**: su `SV_EXPORTACIONES.sv.yaml` respetado
  tal cual + `modelo_exportaciones_analyst.yaml` ENRIQUECIDO (sinónimos del diccionario,
  ANIO/MES/PERIODO, sample_values, custom_instructions con las 7 reglas de calidad,
  8 verified queries con los JOIN completos) + `crear_semantic_view.sql` (plantilla) +
  `subir_yaml_a_stage.sql` + `semantic/preguntas_doradas.yaml` (25 casos, 12 con SQL
  de referencia).
- **F2 · Backend núcleo**: `config.py` (todo por entorno, fail-fast), conexión con
  **PAT o llaves RSA duales con failover**, cliente REST de **Cortex Analyst** (JWT
  oficial o PAT), ejecutor con topes, **validador de solo lectura** (esquemas
  permitidos + LIMIT forzado), **verificador cifra-a-cifra** con degradación a
  plantilla, redactor multi-proveedor (cortex/openai/gemini/groq/openrouter/anthropic),
  reintento único enviando el error exacto al Analyst, telemetría en cola fail-open.
- **F3 · API**: `/api/chat` (SSE por etapas), `/api/exportar/{excel,pptx}`
  (institucionales server-side con advertencia legal), `/api/salud`,
  `/api/proveedores`, `/api/track/*`, `/api/metricas/*` con `X-Admin-Token`
  (comparación en tiempo constante) — *oculto ≠ seguro corregido frente a
  modelo_potencialidad*.
- **F4 · Frontend**: React 18 + Vite + TS estricto; tarjeta de respuesta con SQL
  colapsable, chips de verificación/latencias/proveedor, tabla con truncado
  declarado, descargas, feedback 👍/👎, sugerencias, `/metricas` con Plotly.
- **F5 · Telemetría**: DDL exacto (`sql/02`), vistas del panel (`sql/03`), registro
  de 18 campos por pregunta (incluida la versión semántica usada).
- **F6 · Multi-proveedor (parcial)**: selector en la UI + catálogo por entorno.
- **Operación**: notebooks `Lanzar` y `Publicar` ACTUALIZADOS solo en su Celda A
  (la Celda B genérica quedó intacta), rutas Drive `ProColombia/exportbot`, gates
  `pytest` + `ruff`, repo `github.com/EnriqueForero/exportbot`.

## ⏳ Pendiente (en orden recomendado)
1. **En su cuenta Snowflake (30–45 min)**: correr `sql/01`, `sql/02`, `sql/03`;
   crear la vista semántica (Snowsight con su YAML, o `crear_semantic_view.sql`
   validando sintaxis, o VÍA B stage) y dar los GRANT comentados.
2. **Credenciales**: PAT del usuario `SVC_EXPORTBOT` (o par de llaves) → Secrets
   de Colab / variables de Railway.
3. **F1-cierre · Evaluación real**: `python eval/evaluar.py` contra la cuenta; el
   DoD exige ≥ 90 % — ajustar sinónimos/custom_instructions/VQs hasta pasar. *No
   ejecutable desde este entorno de construcción (sin credenciales): esto es lo
   primero que debe correr usted.*
4. **F7 · Railway**: conectar el repo, variables de `.env.example`,
   `ARRANQUE_ESTRICTO=true`; smoke test `/api/salud` y 5 preguntas doradas.
5. **F6-cierre**: comparación lado a lado de redacciones en la UI (hoy: selector).
6. **Refinamientos**: streaming token a token de la redacción, code-splitting de
   Plotly (bundle actual ~4,8 MB por Plotly), ESLint, autenticación de usuarios
   finales (SSO institucional) si se abre fuera de la GIC, alertas de costos
   (`CORTEX_ANALYST_USAGE_HISTORY`).

## Riesgos abiertos (honestos)
- La **sintaxis exacta** de `CREATE SEMANTIC VIEW` puede variar con su versión de
  cuenta: por eso hay 3 vías y la app soporta vista **o** YAML sin tocar código.
- La integración viva con Cortex Analyst **no se pudo probar aquí** (sin
  credenciales): el cliente sigue la especificación pública y el parseo es
  defensivo, pero la prueba de fuego es `eval/evaluar.py` en su cuenta.
- El verificador de cifras es heurístico (formatos es-CO/en-US, redondeos 0–2
  decimales): puede degradar a plantilla en falsos positivos; se auditan en
  telemetría (`CIFRAS_VERIFICADAS`).
