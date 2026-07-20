# ExportBot — guardrails para agentes de desarrollo

Este archivo es vinculante para cualquier agente de IA o persona que modifique el repositorio.

## Regla principal

Preserve el comportamiento ya validado. Una solicitud visual no autoriza cambios funcionales, de API, seguridad, empaquetado, telemetría, exportación o notebooks. Una modificación solo puede declararse terminada cuando pasa el gate de regresión completo.

## Antes de editar

1. Lea `docs/CONTRATO_DE_REGRESION.md`, `contracts/exportbot_v2_contract.json` y `contracts/openapi_v2_baseline.json`.
2. Clasifique el cambio como `visual`, `funcional`, `contrato/API`, `datos`, `seguridad` o `infraestructura`.
3. Ejecute la línea base y registre el resultado: `python scripts/verificar_regresiones.py --sin-e2e`.
4. Identifique los invariantes afectados. Si no están explícitamente incluidos en el alcance, deben permanecer idénticos.

## Durante la edición

- Cambios `visual`: limite el alcance a `frontend/index.html`, `frontend/src/**/*.tsx`, `frontend/src/**/*.css` y activos visuales. No modifique `frontend/src/api/cliente.ts`, `frontend/src/tipos.ts`, `backend/`, `notebooks/`, `sql/` ni contratos salvo que exista una razón funcional documentada.
- No elimine una capacidad para simplificar la interfaz. Reubicar es aceptable; desaparecer no.
- No cambie una ruta, método, payload, respuesta, encabezado, estado SSE o regla de seguridad sin actualizar el contrato y añadir una prueba de migración.
- Toda corrección de regresión debe incluir una prueba que falle antes de la corrección y pase después.
- No modifique una prueba para hacerla pasar si el contrato no cambió de forma explícita.
- No regenere una línea base visual después de un fallo sin revisar la diferencia y documentar por qué es intencional.

## Criterio de terminado

Ejecute:

```bash
python scripts/verificar_regresiones.py
```

Como mínimo deben pasar:

- contrato de rutas y capacidades;
- pruebas backend;
- lint y formato Python;
- build TypeScript/Vite;
- smoke test del SPA y contrato/build de `/metricas`;
- prueba E2E de consulta, SQL, tabla, exportaciones, feedback y errores;
- comparación visual contra la línea base aprobada.

La compilación por sí sola no demuestra ausencia de regresiones.

## Cambios intencionales de contrato

Cuando una capacidad protegida deba cambiar:

1. documente el motivo y el impacto en `CHANGELOG.md`;
2. actualice `docs/CONTRATO_DE_REGRESION.md` y el JSON contractual;
3. añada o ajuste pruebas que expresen el nuevo comportamiento;
4. regenere OpenAPI únicamente con `python scripts/actualizar_contrato_openapi.py --confirm-contract-change`;
5. incremente versión conforme a SemVer;
6. regenere la línea base visual únicamente después de aprobación explícita.
