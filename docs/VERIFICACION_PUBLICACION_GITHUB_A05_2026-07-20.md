# Verificación A05 — Publicación GitHub y aislamiento de gates

## Incidente reproducido

En Google Colab, `publicar_github()` instaló correctamente el stage y aprobó 27 pruebas, pero la prueba `test_all_protected_api_routes_still_exist` reportó como ausentes nueve rutas. Las pruebas funcionales de esas mismas rutas y el snapshot OpenAPI sí aprobaron. Por tanto, el fallo no representaba pérdida de endpoints: la comprobación dependía de `app.routes`, una estructura interna del framework.

## Corrección

1. La existencia de rutas y métodos se valida sobre `FastAPI.openapi()`, la superficie pública y serializable del contrato.
2. El contrato OpenAPI completo continúa comparándose contra `contracts/openapi_v2_baseline.json`; no se relajó ningún gate.
3. Los subprocesos de gates usan `PYTHONPATH=<stage>/backend:<stage>` y `PYTHONNOUSERSITE=1`, evitando colisiones con módulos globales de Colab.
4. El fail-fast imprime la ruta real de `main.py` importada y cuenta las rutas `/api/*`.
5. `scripts/adaptar_notebooks.py` conserva el mecanismo al regenerar notebooks.

## Resultado esperado en Colab

Antes de pytest debe aparecer una línea similar a:

```text
main= /content/gate_src/backend/main.py rutas_api= 11
```

Después, la suite contractual debe terminar sin el falso positivo de rutas ausentes.
