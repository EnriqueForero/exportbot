# Contrato de regresión de ExportBot

**Línea base:** v2.0.0b2 · revisión A03 con sistema visual de Gestión de Conocimiento.  
**Objetivo:** permitir evolución controlada sin perder capacidades ya validadas.

## 1. Qué demostró la auditoría A02 → A03

Los archivos de `backend/`, `notebooks/`, `sql/`, `eval/`, `scripts/`, `pyproject.toml`, configuración y pruebas Python conservaron exactamente el mismo contenido. Por tanto, el rediseño no alteró la lógica de Snowflake, seguridad SQL, verificación de cifras, exportadores, telemetría, empaquetado ni notebooks.

La interfaz sí cambió código React, no solo CSS. Se modificaron el enrutamiento, el formulario, la presentación del progreso, las tarjetas de respuesta y el panel de métricas. Las capacidades principales se conservaron y se añadieron mejoras —textarea, consultas relacionadas, cierre de sesión y carga diferida de Plotly—, pero había una pérdida menor de información: el número exacto de intentos de autocorrección SQL pasó a mostrarse de forma genérica. A04 lo restaura y añade una explicación visible del propósito del feedback.

Conclusión rigurosa: **no se encontró regresión funcional grave**, pero A03 no tenía evidencia suficiente para garantizarlo porque el frontend solo compilaba; no existían pruebas de interacción ni línea base visual.

## 2. Invariantes funcionales protegidos

### Consulta y respuesta

- Consulta libre, límite de 800 caracteres.
- Envío por botón o Enter; Shift+Enter conserva salto de línea.
- Selección de proveedor cuando hay más de uno disponible.
- Preguntas de referencia y preguntas relacionadas.
- Progreso SSE visible durante la ejecución.
- Error de servidor visible y asociado a la pregunta.
- Respuesta, proveedor/modelo, latencias, verificación y número de intentos.
- SQL ejecutada expandible.
- Tabla completa del resultado recibido y aviso cuando está truncado.
- Descargas Excel y PowerPoint.
- Feedback positivo o negativo una sola vez por respuesta.

### Panel de métricas

- Acceso protegido mediante `ADMIN_TOKEN`.
- Consumo de resumen, series, preguntas y feedback.
- KPIs, gráfico, tablas y cierre de sesión.
- Ruta directa `/metricas` servida por el fallback SPA.

### Backend e infraestructura

- Arranque degradado sin credenciales y fail-fast en modo estricto.
- SQL de solo lectura, esquemas permitidos y límite forzado.
- Verificación anti-alucinación de cifras.
- Exportables válidos sin conexión Snowflake.
- Empaquetado editable y notebooks Colab funcionales.
- Manifiesto de release y bloqueo ante archivos faltantes.

El detalle ejecutable vive en `contracts/exportbot_v2_contract.json`; el contrato de transporte está congelado en `contracts/openapi_v2_baseline.json`.

## 3. Mecanismo de protección

La protección tiene cuatro capas; ninguna sustituye a las demás.

1. **Contrato ejecutable:** prueba rutas, métodos, capacidades y una matriz de trazabilidad. El snapshot OpenAPI detecta cambios silenciosos en payloads y respuestas.
2. **Pruebas de regresión backend:** validan seguridad, configuración, exportadores, API, notebooks y empaquetado.
3. **Prueba E2E en navegador:** simula una consulta real contra APIs controladas y verifica consulta, respuesta, SQL, tabla, descargas, feedback y errores. El panel de métricas queda cubierto por contrato de rutas, pruebas API, comprobaciones estáticas de controles y build de producción.
4. **Regresión visual:** compara la portada renderizada con una captura aprobada. Una diferencia superior al umbral bloquea el CI y exige revisión humana.

El gate provisiona automáticamente el navegador Chromium compatible con la
versión Python de Playwright. El paquete y el navegador son dependencias
separadas; la instalación es idempotente y usa un caché común durante el runtime.
Así, un Colab limpio no falla por ausencia de `chrome-headless-shell`.

El comando único es:

```bash
python scripts/verificar_regresiones.py
```

Para una verificación rápida sin navegador:

```bash
python scripts/verificar_regresiones.py --sin-e2e
```

## 4. Política de cambio

- Un cambio visual no puede modificar contratos de API ni comportamiento funcional.
- Una capacidad puede cambiar solo si el cambio es intencional, documentado, versionado y probado.
- No se actualiza una captura de referencia para "hacer verde" el CI. Primero se inspecciona la diferencia.
- Las pruebas expresan el contrato, no la implementación. Refactorizar es libre mientras el comportamiento permanezca.
- El gate debe ejecutarse sobre la copia exacta que se va a publicar, no sobre un árbol distinto.

## 5. Por qué esto es mejor que congelar archivos por hash

Congelar todo por SHA-256 impediría corregir o mejorar código legítimamente. Los hashes son adecuados para integridad del release, pero no para evolución del producto. Las pruebas de contrato y comportamiento permiten cambiar la implementación conservando el resultado observable; esa es la protección correcta contra regresiones.
