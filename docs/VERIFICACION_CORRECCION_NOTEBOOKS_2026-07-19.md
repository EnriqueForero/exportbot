# Verificación de corrección — notebooks Colab

Fecha: 2026-07-19  
Proyecto: ExportBot 2.0.0b2

## Causas raíz corregidas

1. `pyproject.toml` no tenía `build-system` ni descubrimiento explícito. Setuptools
   interpretaba el monorepo como un *flat layout* con múltiples paquetes de nivel
   superior y bloqueaba el build editable.
2. `Lanzar_App_Colab_Cloudflare.ipynb` verificaba el paquete inexistente
   `registro_analitica`, heredado de otro proyecto.
3. `Publicar_GitHub.ipynb` duplicaba la instalación y llamaba
   `venv/bin/pip`, ejecutable que `uv venv` no garantiza.
4. La verificación estructural y de versiones del publicador conservaba rutas y
   contratos de otro repositorio.
5. El lector del manifiesto esperaba `files_sha256`, pero el generador vigente
   produce una lista `archivos`; la comprobación quedaba vacía y no protegía nada.
6. El generador incluía `dist/`, aunque el stage de GitHub lo excluye, lo cual
   habría producido falsos faltantes al activar correctamente el cotejo.

## Cambios aplicados

- Empaquetado explícito de los módulos planos y paquetes alojados en `backend/`.
- Extra `dev` declarado para compatibilidad con instalación editable.
- Validación de importación contra la distribución `exportbot` y los módulos
  reales: `config`, `main`, `orquestador` y `schemas`.
- Gates con una sola instalación de runtime + desarrollo mediante `uv`.
- Contrato de estructura actualizado a `backend/tests`, `frontend/package.json`,
  ambos notebooks y archivos reales del proyecto.
- Versiones validadas entre PEP 440 (`2.0.0b2`) y base SemVer npm (`2.0.0`).
- Manifiesto compatible con el esquema actual y exclusiones alineadas con stage.
- Pruebas de regresión para evitar que vuelvan las referencias heredadas.

## Evidencia ejecutada

- Build editable aislado con `uv`: aprobado.
- Importación de distribución y módulos: aprobada.
- Simulación de `PY = preparar_entorno(PROYECTO)`: aprobada.
- Simulación de `GATES_OK = correr_gates()`: aprobada.
- Suite backend completa: aprobada.
- Ruff: aprobado.
- Build del frontend con Vite/TypeScript: aprobado.
- Validación de estructura, versiones y manifiesto: aprobada.
