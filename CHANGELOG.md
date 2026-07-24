# Changelog

## [2.0.0] — 2026-07-24 · VERSIÓN FINAL

Consolida el ciclo rc1→rc3 en la versión de producción. Resumen ejecutivo:
- **Telemetría v2** (`DB_EXPORTBOT.TELEMETRY`, estándar GIC): rastro completo
  pregunta→SQL→**respuesta**, middleware HTTP, descargas ligadas al chat,
  identidad (`APP_NAME/APP_VERSION/ENVIRONMENT/USER_ID`) en todas las tablas,
  zona horaria Bogotá a nivel de sesión, bug de versión vacía corregido con test.
- **Credenciales a prueba de incidentes**: cargador de llave tolerante
  (PEM-b64 / DER-b64 / PEM crudo), fail-fast al arranque, y `/api/salud` con
  **identidad efectiva** (cuenta, usuario) + huella de llave(s) — todo 401 se
  diagnostica en un JSON.
- **Exactitud**: `claude-sonnet-4-6` por defecto (verificado en la cuenta),
  literales y sample_values al casing real de la BD, 12 preguntas doradas.
- **Corregido (bloqueaba el publicador de GitHub)**: `pyproject.toml` había
  quedado en 2.0.0b2 mientras `VERSION` avanzaba — versiones ahora unificadas y
  vigiladas por `test_version_coherente.py`.
- **Documentación final**: README reescrito, RUNBOOK con los 8 incidentes reales
  de la puesta en marcha, `docs/guias/` (manual 7 fases, Colab, Railway,
  playbook replicable del patrón).

**Condición de go-live**: eval ≥ 90 % + checklist Fase 7 del manual.

*Build 2 (mismo 2.0.0, pre-publicación):* el gate del publicador detectó 32
hallazgos de lint en `eval/` y `scripts/` (alcance que la verificación local no
cubría) más deriva de versión de ruff (`>=0.6` sin techo). Corregidos con
criterio — hora Bogotá explícita en exportadores, fail-open con rastro en debug,
excepciones concretas en tests, `check=` explícito en subprocess — y **ruff
pinneado a 0.16.0**: el veredicto del gate ya no cambia con cada release de la
herramienta.


## [2.0.0rc3] — 2026-07-24

### Identidad visible (incidente "JWT token is invalid" con huella coincidente)
- `/api/salud` expone ahora `cuenta` y `usuario_snowflake` — la identidad EFECTIVA con
  la que la app firma el JWT. Un 401 con llave correcta significa identidad equivocada;
  ahora se diagnostica mirando un JSON, no adivinando qué hay en los Secrets.
- Si existen ambas llaves, `llave_rsa_2` reporta también la legibilidad de la segunda
  (recordatorio: su pública debe estar en `RSA_PUBLIC_KEY_2` o el failover a esa llave
  producirá 401).


## [2.0.0rc2] — 2026-07-23

### Robustez de credenciales (incidente MalformedFraming)
- Nuevo `snowflake_/llaves.py`: cargador tolerante de la llave privada que acepta
  los TRES formatos reales — PEM-b64 (documentado), **DER-b64** (cuerpo del PEM sin
  cabeceras, el del incidente) y PEM crudo — con mensajes de error en español que
  nombran el formato detectado y la corrección exacta. Driver y JWT de Analyst usan
  la MISMA lógica: un secreto válido lo es en todas las capas.
- **Fail-fast al arrancar**: la app intenta leer la llave, publica el veredicto y la
  huella en `/api/salud` (`"llave_rsa": "legible (SHA256:…)"` / `"ILEGIBLE: …"`) y,
  con `ARRANQUE_ESTRICTO=true`, aborta — un secreto roto grita al desplegar, no en
  la primera consulta del usuario.
- La firma del JWT ahora reporta llave ilegible como `ErrorAnalyst` tipificado
  (mensaje claro en el chat) en lugar del genérico "Error interno".


## [2.0.0rc1] — 2026-07-23

### Telemetría v2 (DB_EXPORTBOT.TELEMETRY — estándar GIC 2026-05-13)
- `CHAT_LOG` guarda ahora el rastro completo: **RESPUESTA final**, `RESPUESTA_DEGRADADA`,
  `LATENCIA_REDACCION_MS`, `USER_ID`, `ENVIRONMENT`, `APP_NAME` y `DETALLES` (VARIANT).
- `EVENTOS_APP` → **`UI_EVENT`** con identidad completa; **corrige el bug** que insertaba
  siempre `''` como versión de la app.
- Nuevo **`DOWNLOAD_EVENT`**: cada descarga (excel/pptx) queda ligada a su `CHAT_LOG_ID`.
- Nuevo middleware **`AuditoriaHTTP`** → `EVENT_LOG`: método, endpoint, status, duración,
  sesión, usuario, IP y user-agent de cada request `/api/*` (fail-open).
- `FEEDBACK` acepta `USER_ID`/`SESSION_ID`; sesión Snowflake con `TIMEZONE=America/Bogota`
  (adiós a los parches `CONVERT_TIMEZONE`).
- DDL canónico: `sql/02_telemetria_v2_ddl.sql` (v1 archivada en `sql/legado/`).

### Modelos y semántica
- Modelo de redacción por defecto: **`claude-sonnet-4-6`** (verificado con
  `SNOWFLAKE.CORTEX.COMPLETE` en la cuenta el 2026-07-23; `mistral-large2` queda como opción).
- Literales y `sample_values` corregidos al **casing real de la BD (MAYÚSCULAS)** en
  `modelo_exportaciones_analyst.yaml` y `preguntas_doradas.yaml` (evita evaluaciones
  con 0 filas). Snapshot de la vista desplegada: `semantic/sv_exportaciones_desplegada_2026-07-23.yaml`.

### API
- `user_id` opcional en `/api/chat`, `/api/exportar/*`, `/api/track/*` (body o cabecera
  `X-User-Id`); contrato OpenAPI regenerado. `/api/salud` expone `entorno`.

 · ExportBot
### A06 — Playwright reproducible en Colab

- El publicador instala y valida automáticamente Chromium antes del gate E2E.
- Se comparte `PLAYWRIGHT_BROWSERS_PATH` entre instalación y pytest.
- Se añade fallback para dependencias Linux en runtimes root como Google Colab.
- El mecanismo queda protegido por pruebas y por el generador de notebooks.



## A05 — 2026-07-20

- Corrige falso positivo del gate de rutas en Colab: validación sobre OpenAPI en lugar de `app.routes`.
- Aísla imports de gates con `PYTHONPATH` del stage y `PYTHONNOUSERSITE=1`.
- Añade diagnóstico del módulo `main` realmente importado antes de publicar.
- Mantiene intacto el contrato OpenAPI y todas las pruebas funcionales.

## 2.0.0b2-regression — 2026-07-20

- Auditoría comparativa A02 → A03: 79 archivos idénticos, 10 modificados y 18 altas/bajas; ningún cambio funcional fuera de `frontend/`, bundles, changelog, manifiesto e informe visual.
- Se restauran dos detalles de trazabilidad perdidos en A03: número exacto de intentos de autocorrección SQL y explicación del propósito del feedback.
- Se incorpora contrato ejecutable de capacidades, matriz de trazabilidad y snapshot OpenAPI para detectar cambios silenciosos de rutas, payloads y respuestas.
- Se añaden pruebas E2E de consulta, SSE, respuesta, SQL, tabla, descargas, feedback y errores, más líneas base visuales de portada y resultado.
- Se incorpora `AGENTS.md`, gate único `scripts/verificar_regresiones.py`, hook pre-push y CI obligatorio para backend, frontend y regresión E2E/visual.
- El notebook de publicación y su generador quedan sincronizados con los nuevos gates y artefactos contractuales.

## 2.0.0b2 — 2026-07-19
Corrección de empaquetado y notebooks Colab (A09): se declara explícitamente el
backend en `pyproject.toml`, se elimina la validación heredada de
`registro_analitica`, los gates instalan con `uv pip --python` sin depender de
`venv/bin/pip`, la verificación usa las rutas reales de ExportBot y el manifiesto
SHA-256 vuelve a validar el esquema que realmente genera el proyecto.

Corrección de despliegue (diagnóstico A08): las plantillas Colab exigen
`pyproject.toml` + `package.json` + `backend/` en la MISMA carpeta y `dist/` en la
raíz; el monorepo b1 tenía ambos dentro de `frontend/` → "0 candidatos" en Lanzar
y Publicar. Cambios: `package.json` proxy en la raíz (build delega a frontend/ y
copia `dist/` a la raíz), el ZIP de release incluye `dist/` en la raíz, el backend
sirve `frontend/dist` o `dist` (el primero que exista) y los notebooks pasan a v3
(detección tolerante a monorepos + mensajes de error con pistas accionables).

## 2.0.0b1 — 2026-07-19
Reescritura completa (v1 Streamlit+GPT-3.5 → arquitectura de estándar internacional):
- SQL generada EXCLUSIVAMENTE por Snowflake Cortex Analyst sobre la vista semántica
  SV_EXPORTACIONES (modelo estrella FACT_EXPORTACIONES_SL, datos 2006-01 a 2026-04).
- Contrato anti-alucinación de 7 capas: semántica gobernada, SQL de solo lectura
  validada (esquemas permitidos + LIMIT), reintento con error exacto, redacción bajo
  contrato, verificación cifra-a-cifra con degradación a plantilla, trazabilidad total.
- Backend FastAPI modular (config por entorno, PAT o llaves RSA duales con failover,
  telemetría asíncrona fail-open, exportadores Excel/PPTX institucionales, SSE).
- Frontend React 18 + Vite + TS estricto: tarjeta de respuesta con SQL visible,
  chips de verificación, descargas, feedback 👍/👎 y panel /metricas con token.
- Operación: Colab efímero (Cloudflare) con dist/ precompilado, Dockerfile + railway.toml,
  CI GitHub Actions, suite de 18 pruebas, ruff limpio, manifiesto SHA-256.

## 1.x — 2024
Prototipo Streamlit (patrón Frosty): regex sobre gpt-3.5, sin validación ni telemetría.

## 2.0.0b2-ui — 2026-07-19

- Rediseño completo del frontend para alinearlo con el sistema visual de Gestión de Conocimiento: navbar institucional blanca, héroe océano, acento ámbar, tipografías Jost/Maven Pro, tarjetas, tablas, avisos y pie legal.
- La consulta deja de usar una barra flotante tipo chat y pasa a una tarjeta institucional con ejemplos, proveedor y resultados trazables.
- Resultados, SQL, exportaciones, feedback y panel de métricas fueron adaptados al mismo lenguaje visual.
- `/metricas` se carga de forma diferida: el bundle inicial baja de ~4,88 MB a ~184 KB; Plotly solo se descarga cuando se abre el panel.
- Se añadieron logos SVG institucionales y ajustes responsivos para escritorio, tableta y móvil.
