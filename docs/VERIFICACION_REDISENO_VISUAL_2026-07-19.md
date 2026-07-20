# Verificación del rediseño visual de ExportBot

Fecha: 19 de julio de 2026  
Versión base: 2.0.0b2

## Alcance

Se reemplazó el sistema visual anterior de ExportBot por uno alineado con el aplicativo Gestión de Conocimiento suministrado como referencia. La adaptación conserva la funcionalidad propia de ExportBot y no copia lógica de negocio del proyecto de referencia.

## Sistema visual incorporado

- Navbar blanca institucional y logos SVG de ProColombia / MinCIT.
- Paleta océano `#011627`, ámbar `#ffa400`, rojo de exportación `#c0392b` y fondo `#fdfffc`.
- Tipografías Jost y Maven Pro, con fuentes de sistema como respaldo.
- Héroe oscuro institucional, KPIs flotantes, tarjetas sobrias, chips, avisos y pie legal.
- Consulta en tarjeta —sin barra flotante tipo chat— y resultados presentados como informe trazable.
- Tablas compactas con encabezado fijo, SQL en bloque oscuro, exportaciones y feedback consistentes.
- Panel `/metricas` adaptado al mismo sistema visual.
- Reglas responsivas para escritorio, tableta y móvil.

## Optimización aplicada

El panel de métricas y Plotly se cargan de forma diferida. El bundle inicial pasó de aproximadamente 4,88 MB a 183,63 KB; el chunk pesado de Plotly solo se solicita al abrir `/metricas`.

## Pruebas ejecutadas

- `npm run build` desde la raíz del monorepo: aprobado.
- TypeScript `tsc -b`: aprobado.
- Vite producción: aprobado.
- Instalación editable Python con `uv`: aprobada.
- Pytest: 22 pruebas aprobadas.
- Ruff lint: aprobado.
- Ruff format check: aprobado.
- Arranque real con Uvicorn: aprobado.
- `GET /api/salud`: HTTP 200 en modo degradado sin credenciales.
- `GET /`: sirve el nuevo HTML institucional.
- Descarga del bundle principal desde FastAPI: HTTP 200.
- Manifiesto de release regenerado después de los cambios.

## Limitación de la verificación

El entorno de ejecución bloqueó por política administrativa la navegación de Chromium tanto a `localhost` como a archivos `file://`. Por esa razón no fue posible adjuntar una captura de pantalla automatizada desde el sandbox. La validación realizada cubre compilación, tipado, estructura DOM/CSS, reglas responsivas declaradas, servicio estático y arranque real; la revisión visual final debe hacerse al abrir el notebook en Colab o al desplegar el ZIP.

## Advertencia no bloqueante

Plotly continúa produciendo un chunk de aproximadamente 4,69 MB. Ya no afecta la carga inicial del chat, pero el panel de métricas seguirá siendo pesado al abrirse. Reducirlo exigiría sustituir Plotly o importar una distribución parcial.
