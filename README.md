# ExportBot 2.0 · ProColombia

Asistente institucional que responde preguntas en **lenguaje natural** sobre las
exportaciones de bienes de Colombia (2006-01 → 2026-04) consultando Snowflake.
La SQL la genera **Cortex Analyst** sobre la vista semántica `SV_EXPORTACIONES`;
el backend **valida** (solo lectura + LIMIT), **ejecuta** con un rol de mínimo
privilegio, **redacta** bajo contrato anti-alucinación, **verifica cada cifra**
contra el resultado (si no puede garantizarla, degrada a plantilla determinista)
y **audita todo** en telemetría.

**Versión:** 2.0.0 · **Python:** 3.11+ · **Stack:** FastAPI + React (Vite) +
Snowflake (Cortex Analyst / COMPLETE) · **Uso interno ProColombia — GIC**

## Principio de diseño

> El LLM **propone**, el código **dispone**. Cortex Analyst solo genera SQL; la
> ejecución, los límites y la verificación viven en este backend. Ninguna cifra
> sin respaldo llega al usuario.

## Arquitectura (7 capas)

```
pregunta → [1] Cortex Analyst (REST+JWT) → [2] guardas solo-SELECT + LIMIT
        → [3] ejecución (rol R_EXPORTBOT_APP) → [4] redacción (claude-sonnet-4-6)
        → [5] verificación cifra a cifra → [6] respuesta + tabla + descargas
        → [7] telemetría DB_EXPORTBOT.TELEMETRY (rastro completo, fail-open)
```

## Inicio rápido

- **Puesta en marcha completa (recomendado):** `docs/guias/06_manual_puesta_en_marcha.md`
  — 7 fases con verificación observable en cada paso + diccionario de 13 errores.
- **Colab + Cloudflare (demo/desarrollo):** `notebooks/Lanzar_App_Colab_Cloudflare.ipynb`
  (Secrets mínimos: `SF_ACCOUNT`, `SF_USER=SVC_EXPORTBOT`, `SF_ROLE`,
  `SF_WAREHOUSE`, `SF_PRIVATE_KEY_B64_1`).
- **Producción (Railway):** `docs/guias/05_guia_railway.md` — deploy desde GitHub,
  `ARRANQUE_ESTRICTO=true`, checklist go-live.
- **Publicar a GitHub:** `notebooks/Publicar_GitHub.ipynb` (gates → vista previa →
  push a rama de trabajo → PR).

## Variables de entorno esenciales

`SF_ACCOUNT`, `SF_USER`, `SF_ROLE`, `SF_WAREHOUSE`, `SF_PRIVATE_KEY_B64_1` (PEM
completo en Base64; desde 2.0.0 también se aceptan DER-b64 y PEM crudo),
`SF_SEMANTIC_VIEW`, `SF_ESQUEMA_TELEMETRIA=DB_EXPORTBOT.TELEMETRY`,
`SF_CORTEX_MODELO=claude-sonnet-4-6`, `ENTORNO_APP` (colab|railway),
`ARRANQUE_ESTRICTO` (true en prod), `ADMIN_TOKEN` (panel /metricas; vacío =
cerrado), `TELEMETRIA_ACTIVA`. Detalle completo: `backend/config.py`.

## Diagnóstico en 5 segundos

`GET /api/salud` publica: estado, **identidad efectiva** (`cuenta`,
`usuario_snowflake`), **legibilidad y huella de la llave RSA** (comparable con
`DESC USER` en Snowflake), entorno y problemas de configuración. Un secreto roto
o una identidad equivocada se ven aquí — no en la primera consulta de un usuario.

## Calidad

- `python scripts/verificar_regresiones.py` — gate único: pytest (41), ruff,
  contrato OpenAPI, build frontend (`--sin-e2e` donde no haya Chromium).
- `eval/evaluar.py --url <app>` — 12 preguntas doradas con SQL de referencia.
  **DoD: ≥ 90 % antes de producción.**
- La versión vive en un solo número (VERSION = pyproject = package.json =
  frontend) vigilado por `backend/tests/test_version_coherente.py`.

## Documentación

- `docs/guias/` — manual de puesta en marcha, guía Colab, guía Railway y
  **playbook replicable** del patrón para otros proyectos del equipo.
- `docs/RUNBOOK.md` — operación e incidentes (síntoma → causa → acción).
- `docs/DECISIONES.md` — registro de decisiones de arquitectura (ADR).
- `CHANGELOG.md` — historial de versiones.

## Estado

**2.0.0** — código completo y probado. Condición de go-live en producción:
eval ≥ 90 % + checklist Fase 7 del manual de puesta en marcha.
