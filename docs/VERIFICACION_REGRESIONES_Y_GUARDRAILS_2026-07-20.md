# Auditoría de regresiones y guardrails de ExportBot

**Fecha:** 20 de julio de 2026  
**Comparación:** A02 corregido → A03 rediseño visual → A04 guardrails  
**Conclusión:** el rediseño A03 no modificó backend, notebooks, SQL, empaquetado, exportadores ni seguridad. Sí cambió lógica de presentación React, y produjo dos regresiones menores de trazabilidad. A04 las corrige y añade controles ejecutables para impedir que cambios futuros borren capacidades ya validadas.

## 1. Alcance y método

La auditoría no se basó en una inspección visual. Se aplicaron cuatro comprobaciones:

1. comparación SHA-256 archivo por archivo entre A02 y A03;
2. diff semántico de los archivos React modificados;
3. ejecución de las suites Python de A02 y A03;
4. pruebas nuevas de contrato, OpenAPI, interacción E2E y regresión visual sobre A04.

Resultado del inventario A02 → A03:

- A02: 93 archivos analizados;
- A03: 103 archivos analizados;
- 79 archivos idénticos;
- 10 archivos modificados;
- 4 archivos retirados, todos bundles frontend reemplazados;
- 14 archivos añadidos, todos activos/componentes/bundles visuales e informe;
- **0 cambios funcionales fuera de frontend, bundles, changelog, manifiesto e informe visual.**

Los 10 archivos modificados fueron `frontend/src/App.tsx`, `ChatPage.tsx`, `MetricasPage.tsx`, `tema.css`, HTML/bundles compilados, `CHANGELOG.md`, `RELEASE_MANIFEST.json` y metadata de TypeScript.

## 2. ¿Hubo regresiones?

### 2.1 Lo que no sufrió regresión

Los hashes de `backend/`, `notebooks/`, `sql/`, `eval/`, `scripts/`, `pyproject.toml`, requisitos, configuración y pruebas Python fueron idénticos entre A02 y A03. Por tanto, el rediseño no pudo alterar directamente:

- autenticación y conexión Snowflake;
- guardas SQL de solo lectura, esquemas y límites;
- verificación anti-alucinación;
- generación Excel y PowerPoint;
- telemetría y métricas backend;
- instalación editable y empaquetado;
- notebooks Colab y gates de publicación.

Además, A02 y A03 aprobaron por separado sus 22 pruebas Python.

### 2.2 Lo que sí cambió funcionalmente en frontend

A03 no fue «solo CSS». Cambió React en aspectos legítimos de experiencia:

- enrutamiento y carga diferida de `/metricas`;
- formulario de consulta y envío por teclado;
- presentación del progreso SSE;
- tarjetas de respuesta, tabla, SQL, feedback y sugerencias;
- autenticación y cierre de sesión del panel de métricas.

Las capacidades centrales se conservaron: consulta, proveedor, progreso, respuesta, SQL, tabla, exportaciones, feedback, errores y métricas. También se añadieron mejoras: `textarea`, Shift+Enter, consultas relacionadas, cierre de sesión y carga diferida de Plotly.

### 2.3 Regresiones reales encontradas

Se encontraron dos pérdidas menores de información:

1. A02 mostraba `SQL corregida (N intentos)`; A03 lo redujo a `SQL autocorregida`, ocultando el número exacto de intentos.
2. A02 explicaba que la calificación alimentaba la auditoría de calidad; A03 eliminó esa explicación.

No son fallos de cálculo ni de seguridad, pero sí reducen trazabilidad y comprensión. A04 restaura ambos elementos y añade pruebas que fallarán si vuelven a desaparecer.

### 2.4 Conclusión correcta

No se encontró una regresión funcional grave. Sin embargo, A03 no podía demostrar ausencia de regresiones frontend: solo compilaba. **Compilar no prueba que botones, SSE, descargas, feedback o errores sigan funcionando.** Esa era la deficiencia de proceso, no necesariamente del producto.

## 3. Qué se tomó de la skill adjunta

La skill `python-data-library-dev` está enfocada en pipelines de datos, pero cuatro principios son aplicables directamente a ExportBot:

1. **VERIFICAR → DIAGNOSTICAR → CORREGIR → VALIDAR.** Primero se registra el comportamiento actual; no se modifica por intuición.
2. **Contrato de paridad antes del refactor.** Se define qué resultados o capacidades deben permanecer iguales.
3. **Golden sets/snapshots.** Una salida aprobada se conserva como referencia y se compara automáticamente.
4. **Gates fail-fast en CI.** Una modificación no se publica si rompe contrato, pruebas, formato o paridad.
5. **Corregir también el generador.** Si un notebook regenera archivos, modificar solo el archivo generado es inútil; la fuente que lo produce debe quedar sincronizada.

Se descartaron como no pertinentes para esta necesidad las reglas específicas de vectorización Pandas, consumo de RAM, PyArrow y checkpointing. Copiarlas al repositorio habría añadido ruido sin proteger la aplicación web.

## 4. Mecanismo implementado

### 4.1 Instrucciones vinculantes para agentes

`AGENTS.md` obliga a cualquier agente o desarrollador a:

- leer el contrato antes de editar;
- clasificar el tipo de cambio;
- limitar cambios visuales al frontend;
- no eliminar capacidades para simplificar;
- no modificar pruebas ni baselines solo para hacerlas pasar;
- ejecutar el gate completo antes de declarar terminado.

La instrucción reduce desorientación de la IA, pero no es el control principal. Un agente puede ignorar texto; por eso la obligatoriedad real está en tests y CI.

### 4.2 Contrato ejecutable y matriz de trazabilidad

`contracts/exportbot_v2_contract.json` enumera:

- 10 rutas API protegidas;
- 16 capacidades frontend;
- 8 invariantes backend;
- evidencia de prueba para cada capacidad/invariante;
- umbrales y archivos de regresión visual.

`backend/tests/test_regression_contract.py` exige que cada requisito tenga evidencia y verifica que las rutas/métodos sigan existiendo.

### 4.3 Snapshot OpenAPI

`contracts/openapi_v2_baseline.json` congela el contrato observable de las rutas protegidas: métodos, parámetros, request bodies, respuestas y esquemas. Un cambio silencioso en payloads o respuestas rompe el gate.

La regeneración no es automática. Solo puede ejecutarse explícitamente con:

```bash
python scripts/actualizar_contrato_openapi.py --confirm-contract-change
```

Esto evita que un agente actualice el baseline para ocultar una incompatibilidad.

### 4.4 Pruebas E2E de comportamiento

`backend/tests/test_frontend_e2e.py` ejecuta el bundle de producción en Chromium con APIs controladas y comprueba:

- carga de portada y selector de proveedor;
- envío de consulta;
- procesamiento SSE;
- respuesta y metadatos;
- número exacto de intentos SQL;
- tabla y SQL expandible;
- Excel y PowerPoint;
- feedback de una sola ejecución;
- error visible y accionable;
- controles protegidos del panel de métricas.

### 4.5 Regresión visual

Se añadieron dos golden snapshots:

- `backend/tests/visual_baselines/exportbot_inicio.png`;
- `backend/tests/visual_baselines/exportbot_resultado.png`.

La prueba compara tamaño y píxeles con tolerancia controlada. Una diferencia estructural superior al 4 % bloquea el gate; la comparación reduce escala y suaviza antialiasing para evitar falsos positivos entre navegadores Linux. El baseline no debe actualizarse sin revisión visual explícita.

### 4.6 Gate único, pre-push y CI

Comando único:

```bash
python scripts/verificar_regresiones.py
```

El gate ejecuta:

- pytest backend/contratos;
- Ruff lint y formato;
- `npm ci`;
- build TypeScript/Vite;
- E2E y visual regression.

También se añadió un hook `pre-push` y tres jobs de GitHub Actions: backend, frontend y E2E-regression.

### 4.7 Notebooks y generadores sincronizados

`Publicar_GitHub.ipynb` ahora exige el gate completo y bloquea publicaciones sin contratos, snapshots o scripts de regresión. `scripts/adaptar_notebooks.py` fue actualizado en paralelo para que una regeneración futura no borre estas correcciones.

## 5. Validaciones ejecutadas en A04

- Comparación SHA-256 A02/A03: completada.
- A02: 22 pruebas aprobadas.
- A03: 22 pruebas aprobadas.
- A04 backend/contratos: 28 pruebas aprobadas, 1 E2E separada.
- A04 E2E y visual: 1 prueba aprobada en Chromium.
- Ruff check: aprobado.
- Ruff format: aprobado.
- Instalación editable e imports: aprobados.
- Arranque real Uvicorn: aprobado.
- `/api/salud`: HTTP 200 en modo degradado.
- `/` y `/metricas`: fallback SPA servido correctamente.
- Sintaxis de bundles compilados: aprobada con Node.
- Validación JSON de ambos notebooks: aprobada.

El build A03 había sido validado antes del presente cambio. En A04 no se pudo repetir localmente `npm ci && npm run build` porque el registro npm del entorno de ejecución no entregó todas las dependencias; por ello el bundle A03 validado fue parcheado de forma equivalente y ejecutado en Chromium. El CI añadido sí reconstruye desde fuente y debe ser obligatorio antes de fusionar o publicar.

## 6. Lo que todavía debe configurarse fuera del código

El CI no es una barrera si GitHub permite fusionar o hacer push ignorándolo. Debe protegerse la rama principal y marcar como requeridos los checks:

- `backend`;
- `frontend`;
- `e2e-regression`.

Además, debe bloquearse el push directo a la rama principal o exigirse pull request. Sin esa configuración, existe control técnico pero no enforcement organizacional.

## 7. Referencias técnicas

- Pytest, prácticas e integración: https://docs.pytest.org/en/stable/
- Playwright, pruebas E2E: https://playwright.dev/python/docs/intro
- Playwright, comparación visual: https://playwright.dev/docs/next/test-snapshots
- OpenAPI Specification: https://spec.openapis.org/oas/
- GitHub, ramas protegidas: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub, status checks: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks
- Semantic Versioning: https://semver.org/

## 8. Dictamen

A04 es más segura que A03 porque transforma una intención —«no dañar lo que ya funciona»— en un contrato verificable. No existe garantía absoluta de cero regresiones; sí existe ahora una barrera razonable y estándar que detecta cambios en API, comportamiento, interacción y apariencia antes de publicar.
