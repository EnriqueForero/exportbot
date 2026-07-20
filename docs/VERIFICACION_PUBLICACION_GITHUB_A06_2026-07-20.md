# Verificación A06 — Playwright reproducible en Colab

**Fecha:** 20 de julio de 2026  
**Proyecto:** ExportBot 2.0.0b2  
**Alcance:** corrección del gate E2E de `notebooks/Publicar_GitHub.ipynb`

## 1. Incidente reproducido

El publicador instalaba `playwright==1.57.0` como dependencia Python y después ejecutaba la prueba E2E. En un runtime limpio de Google Colab no existía el binario esperado por esa versión:

```text
/root/.cache/ms-playwright/chromium_headless_shell-1200/
chrome-headless-shell-linux64/chrome-headless-shell
```

Por tanto, el gate fallaba antes de abrir la aplicación. No era una regresión de ExportBot ni un fallo de la prueba visual; era una dependencia de runtime ausente.

Playwright distribuye la librería y los navegadores como componentes separados. La instalación oficial para Linux/CI exige instalar también el navegador y, cuando corresponda, sus dependencias del sistema:

- https://playwright.dev/python/docs/browsers
- https://playwright.dev/python/docs/ci

## 2. Corrección aplicada

Se añadió `scripts/playwright_runtime.py`, responsable de:

1. definir un único `PLAYWRIGHT_BROWSERS_PATH` para instalación y ejecución;
2. intentar primero un Chromium/Chrome ya disponible en el sistema;
3. si no existe, ejecutar con el mismo Python del venv:

   ```bash
   python -m playwright install chromium
   ```

4. lanzar y cerrar el navegador como prueba funcional;
5. si el binario existe pero faltan bibliotecas Linux y el runtime permite instalarlas, ejecutar:

   ```bash
   python -m playwright install-deps chromium
   ```

6. bloquear el gate con diagnóstico completo si Chromium continúa sin arrancar.

El notebook llama este aprovisionador antes de pytest y transmite el mismo entorno a la prueba E2E. La prueba no se omite, no se marca como `skip` y conserva la comparación visual.

## 3. Persistencia de la corrección

La corrección se incorporó en cuatro niveles:

- `notebooks/Publicar_GitHub.ipynb`: aprovisiona Chromium dentro de `correr_gates()`.
- `scripts/playwright_runtime.py`: implementación única e idempotente.
- `scripts/verificar_regresiones.py`: el gate local usa el mismo mecanismo.
- `scripts/adaptar_notebooks.py`: una regeneración futura del notebook conserva la corrección.

Además, `backend/tests/test_notebook_contracts.py` y `backend/tests/test_playwright_runtime.py` protegen el mecanismo contra regresiones.

## 4. Validaciones ejecutadas

### Gate exacto del notebook

Se extrajeron y ejecutaron las celdas reales del notebook A06 sobre una copia limpia del proyecto, con venv y stage nuevos.

Resultado:

```text
main= /tmp/a06_gate_src/backend/main.py rutas_api= 11
31 passed, 1 deselected
All checks passed!
36 files already formatted
npm ci: 335 paquetes
Vite: build aprobado
Chromium: arrancó y cerró correctamente
E2E/visual: 1 passed
Gates aprobados (6 comandos)
RESULT True
```

### Pruebas adicionales

- Pruebas backend no E2E: **31 aprobadas**.
- Prueba E2E y regresión visual: **1 aprobada**.
- Ruff lint: aprobado.
- Ruff format: aprobado.
- Build TypeScript/Vite: aprobado.
- Notebook: JSON válido y todas sus celdas Python compilan.
- Prueba unitaria del camino “navegador ausente → instalar → volver a probar”: aprobada mediante simulación controlada, sin depender de red.
- Arranque con navegador de sistema disponible: aprobado.

El entorno de validación no permitió descargar desde el CDN de Playwright para repetir una descarga real. Ese camino quedó cubierto mediante prueba unitaria de comandos y estado; la descarga real se ejecutará en Colab, que ya demostró acceso de red al instalar 335 paquetes npm.

## 5. Comportamiento esperado en Colab

En el primer runtime limpio aparecerá algo similar a:

```text
🌐 Chromium no está disponible; instalando la versión compatible con Playwright…
$ .../python -m playwright install chromium
✅ Chromium instalado y validado
```

En ejecuciones posteriores dentro del mismo runtime:

```text
🌐 Chromium de Playwright disponible
```

El caché se ubica en `/content/.cache/ms-playwright`. Al reiniciar completamente Colab, `/content` se elimina y el navegador debe descargarse de nuevo. Esto es deliberado: evita guardar cientos de MB de binarios específicos de Linux dentro de Google Drive o del repositorio.

## 6. Impacto en GitHub y Railway

No se modificaron rutas API, frontend funcional, contrato OpenAPI, Dockerfile, `railway.toml`, configuración de Snowflake ni lógica de despliegue. La corrección afecta exclusivamente el aprovisionamiento del navegador de pruebas y los controles que lo protegen.

GitHub Actions ya usaba `python -m playwright install --with-deps chromium`; se mantuvo sin cambios porque era correcto.
