# Changelog · ExportBot
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
