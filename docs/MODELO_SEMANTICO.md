# Modelo semántico · contrato de flexibilidad

**Principio**: el conocimiento del negocio vive en la CAPA SEMÁNTICA, no en el
código. Cambiar de base, renombrar columnas o añadir métricas se resuelve editando
la vista/YAML y variables de entorno — el backend no se toca.

## Archivos
- `semantic/SV_EXPORTACIONES.sv.yaml` — SU original (FastGen + 9 relaciones a mano).
  Se conserva intacto como fuente de verdad de la estructura.
- `semantic/modelo_exportaciones_analyst.yaml` — el anterior ENRIQUECIDO (aditivo):
  sinónimos del diccionario, ANIO/MES_NUMERO/PERIODO derivados de WK_MES,
  sample_values, custom_instructions (7 reglas) y 8 verified queries con JOINs.
- `semantic/preguntas_doradas.yaml` — contrato de exactitud (≥ 90 %).
- `docs/DICCIONARIO_FACT_EXPORTACIONES.md` — diccionario oficial de la estrella.

## Cómo evolucionarlo
1. **Nueva pregunta que falla** → mírela en CHAT_LOG → si el Analyst eligió mal
   columna/join: añada un sinónimo o una verified query con la SQL correcta →
   re-suba el YAML (o edite la vista) → `python eval/evaluar.py`.
2. **Cambia la base** (p. ej. nueva capa GOLD): duplique el YAML, ajuste
   `base_table` y relaciones, cree la vista `SV_X`, apunte `SF_SEMANTIC_VIEW`.
   El validador acepta el nuevo esquema vía `SF_DATABASE/SF_SCHEMA` o
   `ESQUEMAS_PERMITIDOS`. Cero código.
3. **Nueva métrica/dimensión**: añádala al YAML con description+synonyms; si es
   crítica, acompáñela de una verified query y un caso dorado.
4. **Decisiones ya tomadas que NO debe romper**: sin DIM_FECHA_SL (fan-trap
   diario vs mensual); un solo camino a departamento (ORIGEN) y a transporte
   (TRANSPORTE) — procedencia/logística solo como columnas del hecho; variables
   "estrella" = atributo de EMPRESA.

## Nota técnica
Su generador emitió `facts:`; el enriquecido mantiene esa forma por compatibilidad
probada. Si migra al esquema `measures` con `default_aggregation: sum`, hágalo en
una copia y valide con la suite dorada antes de reemplazar.
