# Registro de decisiones (ADR) · ExportBot 2.0

Complementa D1–D10 del plan (`PLAN_EXPORTBOT_2.md` §3). Decisiones tomadas o
ajustadas DURANTE la construcción:

- **A1 · PAT además de llaves RSA.** El plan asumía solo key-pair; se añadió
  Programmatic Access Token como vía prioritaria (más simple para Colab/Railway,
  cumple el bloqueo 2025-2026 de contraseñas single-factor). Config decide sola:
  `SF_PAT` presente → PAT; si no, llaves con failover 1→2.
- **A2 · Fuente semántica dual.** `SF_SEMANTIC_VIEW` (objeto en cuenta) o
  `SF_SEMANTIC_MODEL_FILE` (YAML en stage). Motivo: la sintaxis DDL de semantic
  views evoluciona; el YAML es la ruta gobernable por Git. Cambiar de base = crear
  otra vista/YAML y cambiar UNA variable.
- **A3 · YAML enriquecido ADITIVO.** Se respetó la estructura exacta que generó
  su FastGen (`facts:`, mismas 10 tablas y 9 relaciones) y solo se AÑADIÓ
  metadata (synonyms, descriptions, sample_values, custom_instructions, VQs).
  Motivo: esa forma ya está validada por el generador en su cuenta; migrar a
  `measures/default_aggregation` queda documentado como opción futura.
- **A4 · CSS con tokens en vez de Tailwind.** El plan dejaba Tailwind "por
  decidir". Se eligió CSS propio con variables: cero dependencias de build extra,
  compilación más rápida y robusta en el flujo efímero de Colab, identidad
  institucional igual de lograda. Reversible sin tocar la lógica.
- **A5 · SSE por etapas (no token a token).** El flujo emite eventos
  analyst→validación→sql→ejecución→redacción→final. Percepción de progreso sin
  la complejidad de streaming del LLM; el streaming fino queda como refinamiento.
- **A6 · Sin pandas/pyarrow en runtime.** El ejecutor entrega listas nativas:
  arranque en Colab minutos más rápido y menos superficie de dependencias; los
  exportadores consumen columnas+filas directamente.
- **A7 · Un reintento máximo con el error exacto.** Igual que gestion_conocimiento:
  el error del motor viaja al Analyst como turno adicional; más de un reintento
  esconde problemas del modelo semántico que deben arreglarse EN el modelo.
- **A8 · Notebooks: solo Celda A.** Sus plantillas declaran "Celda B no se toca";
  la adaptación fue quirúrgica por regex sobre la Celda A y el encabezado,
  preservando su pipeline endurecido (saneo de lockfiles, latidos, timeouts).
