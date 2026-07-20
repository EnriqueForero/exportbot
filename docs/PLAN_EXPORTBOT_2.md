# ExportBot 2.0 — Plan de Trabajo Riguroso
**Versión 1.0 · 2026-07-19 · Hoja de ruta técnica y estratégica para la modernización del chatbot de exportaciones de ProColombia**

---

## 0. Veredicto inicial del asesor (léalo antes que nada)

ExportBot v1 fue un buen primer ejercicio hace dos años; hoy es un pasivo técnico. Es una adaptación del tutorial "Frosty" de Snowflake: `gpt-3.5-turbo` (modelo retirado del mercado), extracción de SQL por expresión regular, sin validación de la SQL generada, sin registro de nada, sin autenticación, y con la precisión dependiendo por completo de un prompt de texto plano. Nada de eso sobrevive a 2026.

La buena noticia, y esto lo digo sin halago porque es un hecho verificable en el código: **usted ya construyó, en sus otros cuatro repositorios, casi todas las piezas de calidad de producción que ExportBot 2.0 necesita.** Este plan no inventa; ensambla lo mejor de su propio portafolio sobre una decisión nueva y central: reemplazar la generación de SQL "a mano por prompt" por **Snowflake Cortex Analyst con modelo semántico**, que es el mecanismo oficial de Snowflake para texto-a-SQL de alta precisión.

Dos verdades incómodas que el plan asume desde el inicio:

- **"Cero alucinaciones" absoluto no existe** en ningún sistema con LLM. Lo que sí existe, y es lo que este plan compra, es un contrato verificable: *ninguna cifra en la respuesta puede provenir de un lugar distinto al resultado de la SQL ejecutada y mostrada*, más una exactitud **medida** contra una suite de preguntas doradas antes de cada release. Eso es auditable; "cero alucinaciones" es un eslogan.
- **Una página "oculta" no es una página segura.** Su propio código del modelo de potencialidad lo admite en un comentario ("Cuando exista SSO, agregar guardia por rol de admin"). En 2.0, `/metricas` va protegida con credencial, no con oscuridad.

---

## 1. Diagnóstico: auditoría de los cinco activos

### 1.1 exportbot-main (el punto de partida)
- **Qué es**: Streamlit, 3 archivos (~600 líneas). `prompts.py` construye un system prompt con la descripción de `VISTA_EXPORTACIONES_LONG` (2018–2024) más el diccionario `VISTA_DEFINICIONES_VARIABLES`; `frosty_app.py` llama a OpenAI, extrae la SQL con regex ```` ```sql ```` y la ejecuta con `st.connection("snowflake")`; exporta a Word.
- **Qué se rescata**: (a) el conocimiento de negocio embebido: descripción de la tabla, reglas ("comillas dobles en columnas", "ilike para texto", "no responder requisitos de exportación", límite de 10 filas), y el patrón de leer el diccionario de variables desde Snowflake; (b) los logos y el texto de advertencia legal institucional; (c) la idea del botón de descarga del resultado.
- **Qué se desecha y por qué**:
  - `gpt-3.5-turbo`: modelo obsoleto y retirado.
  - Extracción por regex y ejecución directa sin validar: si el modelo genera un `DELETE` o una columna inexistente, la app lo ejecuta o revienta. Riesgo inaceptable.
  - Sin registro de consultas: usted hoy no puede responder "¿qué preguntan los usuarios y qué tan bien respondemos?" — que es exactamente el objetivo de auditoría que pidió.
  - `st.secrets` con password: Snowflake está bloqueando la autenticación de un solo factor por contraseña (ver §2, D6).

### 1.2 Tres Ejes (`app-tres-ejes-deploy-main`)
- **Se reutiliza**: `src/snowflake_analitica/streamlit_snowflake.py` — el patrón de conexión más maduro del portafolio: llave privada RSA leída desde variable de entorno en Base64 (diseñado para Railway), **doble llave con failover automático ante error JWT**, reintentos solo en errores transitorios, `query_tag` para trazabilidad en Snowflake, timeout de sesión. Se portará de Streamlit a FastAPI (quitando `st.session_state`).
- **Se reutiliza como concepto**: las tablas de eventos (`SEGUIMIENTO_EVENTOS`, `AUDITORIA_CARGUES`) — la idea de que cada botón y cada carga deja huella en Snowflake.
- **Se desecha**: los `INSERT` construidos con f-strings (riesgo de inyección y de romperse con comillas; su propio código tiene que "limpiar comillas simples" a mano, síntoma del problema) y el procedimiento `GET_NEXT_ID()` para IDs (innecesario: `UUID_STRING()` o `IDENTITY`). En 2.0: binds parametrizados siempre.

### 1.3 Modelo de potencialidad (`app/`)
- **Se reutiliza**: 
  - La **arquitectura frontend/backend separada** desplegada en Railway con FastAPI + React 18 + react-router + Plotly, y la página `/metricas` como ruta lazy sin enlace en la barra de navegación.
  - `backend/telemetry.py`: el mejor patrón de telemetría del portafolio — esquema `TELEMETRY` (EVENT_LOG / DOWNLOAD_EVENT / FILTER_EVENT), inserts **asíncronos que nunca bloquean ni rompen la respuesta** (fail-open), conexión dedicada, middleware que captura cada request, binds parametrizados.
  - `pool.py`, `cache.py`, la estructura de `routers/`, los tests de routers.
- **Se desecha**: 
  - **Create React App + craco**: el equipo de React lo declaró oficialmente en retiro (febrero 2025) y recomienda migrar; ya no recibe mantenimiento. 2.0 nace en **Vite**. Fuente: https://react.dev/blog/2025/02/14/sunsetting-create-react-app
  - Generar Excel/PPTX **en el navegador** (`xlsx`, `pptxgenjs`): infla el bundle, duplica lógica de formato y la librería `xlsx` de npm ha arrastrado avisos de seguridad. En 2.0 los archivos se generan **en el servidor** (patrón de gestion_conocimiento y del perfilador), con una sola fuente de verdad de formato institucional.
  - Telemetría con un thread nuevo por insert: funciona, pero bajo ráfagas crea threads sin límite. En 2.0: **una cola en memoria + un worker** (mismo fail-open, consumo acotado).

### 1.4 gestion_conocimiento
Es la joya conceptual para este proyecto. **Se reutiliza**:
- La idea central que usted mismo documentó en `registro_analitica/semantica.py`: replicar el enfoque de **Cortex Analyst** — no darle al LLM el esquema crudo sino un **modelo semántico** (YAML versionado, validado con Pydantic) con descripciones de negocio, **sinónimos**, valores de muestra por cardinalidad y consultas verificadas. En 2.0 dejamos de "replicar la idea" y usamos el producto real de Snowflake (§2, D1).
- `engine/validador.py` + `orquestador.py`: validación de solo-lectura, **"válvula de esquema"** que rechaza columnas alucinadas con feedback rico, y **un reintento enviando el error exacto** al modelo. Esto se conserva como cinturón de seguridad *aunque* Cortex Analyst genere la SQL.
- `integraciones/proveedores.py` + `llm.py`: catálogo multi-proveedor server-side (Gemini, Groq, Cerebras, OpenRouter vía interfaz compatible OpenAI), claves solo en el servidor, listado en vivo de modelos.
- `sql/ddl_snowflake.sql`: el mejor DDL de auditoría del portafolio (`CONSULTAS_LOG` con pregunta/SQL/éxito/proveedor/duración/versión, `EVENTOS_USO` con `VARIANT`, y **vistas de consumo** `V_CONSULTAS_DIARIAS`, `V_PREGUNTAS_TOP`). 2.0 lo extiende (§5).
- `export/excel.py` y el router `exportar.py` (descarga server-side con `Content-Disposition`).
- Higiene de repo: pre-commit, CI, CHANGELOG, `.env.example`, Dockerfile.

### 1.5 perfilador_de_empresas
- **Se reutiliza**: `integraciones/cortex_llm.py` — llamar a `SNOWFLAKE.CORTEX.COMPLETE()` como proveedor de IA *dentro* de Snowflake (con `temperature=0` y validación Pydantic), con el argumento institucional clave que usted ya escribió: *con Cortex, el texto analizado no sale de su cuenta de Snowflake*. También: el router multi-proveedor con round-robin/circuit breaker (`vendor/perfilador/extraccion_llm.py`), `exportacion/excel_institucional.py` y `exportacion/pptx_digest.py` (plantillas PPTX con branding), `snowflake_db.py` (rotación de llaves), y el patrón de `routers/observabilidad.py`.

### 1.6 Definiciones_variables.xlsx
Diccionario de ~25 variables de `VISTA_EXPORTACIONES_LONG`: dimensiones (Año 2018–2024, País destino, Continente, Zona geográfica, HUB, Departamento origen, Cadena/Sector/Subsector/Tipo y sus variantes "estrella" por NIT, Medio de transporte, TLC, Posición arancelaria, NIT, Razón social, Economía naranja, Cadena frío) y la medida `VALOR` (dólares FOB). **Este archivo es la materia prima directa del modelo semántico** (§6): definiciones → `description`, "Unique Values" → valores de muestra/sinónimos, variables `*` → medidas por empresa.

---

## 2. Decisiones de arquitectura (con las alternativas descartadas)

> Formato: **Decisión → alternativas consideradas → por qué se descarta cada una.** Aquí está el 80 % del valor estratégico del plan.

**D1 — Motor texto-a-SQL: Snowflake Cortex Analyst (API REST), no prompt manual.**
- *Qué es*: servicio administrado y agéntico de Snowflake que recibe la pregunta + un modelo semántico y devuelve la SQL; Snowflake reporta >90 % de exactitud en casos reales con modelo semántico, cerca del doble que generación de un solo prompt con un LLM genérico. Fuentes: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst · https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/
- *Alternativa A: mantener el enfoque v1 (prompt con esquema + LLM externo).* Descartada como motor principal: es exactamente lo que produce alucinaciones de columnas y métricas; usted ya lo vivió. Se conserva **solo** como *modo de contingencia* degradado (bandera `MOTOR=fallback`) si Cortex Analyst no estuviera disponible en la cuenta, reutilizando el validador de gestion_conocimiento.
- *Alternativa B: frameworks externos (LangChain SQL agents, Vanna, etc.).* Descartada: agrega una dependencia pesada de terceros para resolver algo que la propia plataforma donde viven los datos ya resuelve mejor, con gobernanza y facturación integradas.
- *Costo a vigilar*: Cortex Analyst se factura **por mensaje** y la SQL generada se ejecuta además en su warehouse (dos componentes de costo). El plan incluye monitoreo con `CORTEX_ANALYST_USAGE_HISTORY` y registro de costos por consulta (§5). Fuente: https://seemoredata.io/blog/snowflake-cortex-analyst-query-history-monitoring/

**D2 — Modelo semántico como Vista Semántica en base de datos; YAML como respaldo versionado.**
- Snowflake dirige las implementaciones nuevas hacia **Semantic Views** (objeto de esquema que guarda entidades, métricas, relaciones y sinónimos dentro de la base), manteniendo compatibilidad con el YAML clásico. Estrategia: el YAML vive en el repositorio (`semantic/modelo_exportaciones.yaml`) como fuente versionada y revisable en PRs; un script lo materializa como Semantic View en despliegue. Así obtiene gobernanza en Snowflake **y** control de versiones en Git. Fuentes: https://seemoredata.io/blog/snowflake-cortex-analyst-query-history-monitoring/ · https://www.snowflake.com/en/blog/engineering/agentic-semantic-model-text-to-sql/
- *Alternativa descartada*: seguir con el "modelo semántico casero" de gestion_conocimiento como motor. Fue el prototipo correcto; mantenerlo ahora sería reinventar con menos precisión lo que la plataforma ya ofrece administrado.

**D3 — Backend: FastAPI (Python 3.12).**
- *Por qué*: tres de sus cuatro repos modernos ya son FastAPI; el conector de Snowflake, openpyxl y python-pptx son Python; su skill de estándares es Python. Cambiar de lenguaje destruiría reutilización sin ganar nada.
- *Alternativa descartada*: Node/Next full-stack — obligaría a reescribir conexión Snowflake, exportadores y validador, y a mantener dos ecosistemas de estándares.

**D4 — Frontend: React 18 + Vite + TypeScript.**
- Vite reemplaza a CRA/craco (retirado oficialmente; ver §1.3). TypeScript en modo `strict`: en el perfilador ya lo usa; los errores de contrato entre frontend y backend se cazan en compilación, no en producción.
- *Gráficas*: Plotly (react-plotly.js) — su equipo ya lo domina y las necesidades (barras, líneas, torta en /metricas y en respuestas) no justifican aprender otra librería.
- *Estilos*: recomendación **Tailwind CSS v4 + tokens de diseño propios** (velocidad, consistencia, tema institucional centralizado). Alternativa válida si prioriza continuidad con potencialidad: styled-components. **Decisión suya antes de F3** (§12); el plan asume Tailwind.

**D5 — Despliegue en Railway: monorepo, un (1) servicio.**
- FastAPI sirve la API bajo `/api/*` y los estáticos del build de React en `/` (patrón que gestion_conocimiento ya insinúa con su `index.html` + backend). 
- *Por qué un servicio y no dos (como potencialidad)*: mismo dominio → sin CORS, sin doble facturación de contenedor, un solo healthcheck, `/metricas` protegida en el mismo perímetro. 
- *Cuándo se rompería esta decisión*: si más adelante quiere CDN/edge para el frontend o equipos separados desplegando a ritmos distintos. Documentado como ADR para revertir sin drama. Referencia Railway: https://docs.railway.com

**D6 — Autenticación a Snowflake: usuario de servicio + par de llaves RSA con rotación dual. Obligatorio, no opcional.**
- Snowflake está eliminando el inicio de sesión por contraseña de un solo factor (hitos de bloqueo desde noviembre de 2025 y cierre definitivo durante 2026); los usuarios de servicio deben usar llave RSA, OAuth, PAT o WIF. Su patrón de Tres Ejes/gestion (dos llaves `SF_PRIVATE_KEY_B64_1/2` con failover ante error JWT) es exactamente la práctica correcta y se adopta tal cual, portado a FastAPI. Fuentes: https://docs.snowflake.com/en/user-guide/key-pair-auth · https://keebo.ai/blog/snowflake-multi-factor-key-pair-authentication/ · https://support.esri.com/en-us/knowledge-base/what-are-esri-s-recommendations-to-mitigate-potential-d-000035129 · https://docs.snowflake.com/en/user-guide/programmatic-access-tokens
- Rol de mínimo privilegio: `ROL_EXPORTBOT` con `SELECT` sobre la vista de exportaciones + `INSERT` sobre el esquema de telemetría + rol de base de datos `CORTEX_ANALYST_USER`. Nada más. Ni `CREATE`, ni `DELETE`, ni acceso a otros esquemas.

**D7 — Multi-proveedor de IA: separación estricta de roles.**
- **La SQL sale siempre y únicamente de Cortex Analyst** (una sola fuente de verdad numérica). Los proveedores externos (Cortex COMPLETE por defecto; OpenAI, Anthropic, Gemini, Groq vía el catálogo de gestion/perfilador) se usan **solo para la capa de redacción** — convertir el resultado tabular en explicación en español — y para el **modo comparación**: misma pregunta, misma SQL, mismos datos, dos redacciones lado a lado con latencia y costo de cada una. Así "se puede comparar" sin sacrificar precisión.
- *Alternativa descartada*: dejar que cada proveedor genere su propia SQL para comparar. Eso convierte la comparación en una lotería de esquemas alucinados y multiplica el costo de warehouse. La comparación útil es de *redacción y servicio*, no de aritmética.
- Redacción bajo contrato: el prompt de redacción recibe **solo** el resultado de la consulta (más la pregunta) con la instrucción dura de no introducir cifras externas; validador posterior verifica que todo número citado exista en el resultado (tolerancia de formato). Si el proveedor externo falla → fallback automático a Cortex COMPLETE (círculo del perfilador).

**D8 — Telemetría y auditoría: esquema propio en Snowflake, inserts asíncronos con cola, binds parametrizados.** Detalle en §5. Fail-open: la telemetría jamás tumba una respuesta (regla ya probada en potencialidad y gestion).

**D9 — /metricas protegida.** Ruta sin enlace en la navegación **y además** detrás de credencial (mínimo viable: token de administrador en variable de entorno pedido en un formulario simple; endpoints `/api/metricas/*` lo exigen en header). Cuando ProColombia habilite SSO, se cambia el guardián sin tocar el dashboard.

**D10 — Flexibilidad ante columnas/tablas futuras (su requisito de "vivir en el tiempo").**
- Regla de oro: **ningún nombre de columna de negocio en el código.** Todo el vocabulario vive en `semantic/modelo_exportaciones.yaml`. Nueva columna en Snowflake = editar YAML + agregar 2–3 preguntas doradas + correr la evaluación + desplegar. Nueva tabla = nuevo bloque en el YAML con sus relaciones. El código (backend y frontend) es agnóstico: renderiza cualquier tabla de resultados y cualquier métrica declarada.
- `VERSION_SEMANTICA` se registra en cada consulta (patrón de gestion) para poder auditar "qué sabía el bot cuando respondió esto".

---

## 3. Arquitectura objetivo

```
Usuario ──► React (Vite, TS, Tailwind, Plotly)
              │  SSE streaming
              ▼
        FastAPI (Railway, 1 servicio)
        ├── /api/chat ──► Orquestador
        │       1. Cortex Analyst API (pregunta + Semantic View) → SQL
        │       2. Validador local (solo lectura, columnas, LIMIT)   [cinturón]
        │       3. Ejecutor Snowflake (timeout, tope de filas)
        │       4. Redactor (Cortex COMPLETE | proveedor elegido)    [contrato]
        │       5. Verificador de cifras (números ⊆ resultado)
        ├── /api/exportar/{excel|pptx}  (server-side, branding)
        ├── /api/metricas/*  (protegido por token)
        ├── /api/track/*     (eventos del frontend)
        └── static/          (build de React)
              │
              ▼
        Snowflake ── VISTA_EXPORTACIONES_LONG (+ vista ancha, §6)
                  ── SEMANTIC VIEW EXPORTACIONES
                  ── TELEMETRIA.{CHAT_LOG, EVENTOS_APP, FEEDBACK} + vistas V_*
```

**Estructura de monorepo propuesta**

```
exportbot/
├── backend/
│   ├── main.py · config.py (dataclass, todo por entorno)
│   ├── snowflake_/ {conexion.py (llaves duales), ejecutor.py, analyst.py, telemetria.py}
│   ├── motores/   {redactor.py, proveedores.py (catálogo), verificador_cifras.py, validador_sql.py}
│   ├── routers/   {chat.py, exportar.py, metricas.py, track.py, salud.py}
│   ├── exportadores/ {excel.py, pptx.py, plantillas/}
│   └── tests/
├── frontend/  (Vite + React + TS: pages/{Chat, Metricas}, components/, api/, theme/)
├── semantic/  {modelo_exportaciones.yaml, materializar_semantic_view.sql, preguntas_doradas.yaml}
├── sql/       {01_roles.sql, 02_telemetria_ddl.sql, 03_vistas_metricas.sql}
├── eval/      {evaluar.py  → exactitud vs preguntas_doradas.yaml}
├── docs/      {ADR-001…, RUNBOOK.md, MODELO_SEMANTICO.md}
├── Dockerfile · railway.toml · .github/workflows/ci.yml · CHANGELOG.md
```

---

## 4. Contrato anti-alucinación (siete capas, todas obligatorias)

- **Capa 1 — Modelo semántico rico**: descripciones de negocio, sinónimos en español ("ventas externas", "FOB", "despachos" → VALOR; "EE. UU.", "USA", "Estados Unidos" → país), valores enumerados para dimensiones de baja cardinalidad, instrucciones custom ("los años válidos son 2018–2024; si preguntan por otro año, decláralo"), y **consultas verificadas** (VQR) que anclan los patrones frecuentes.
- **Capa 2 — SQL solo de Cortex Analyst** (D7): nunca de un LLM genérico en producción.
- **Capa 3 — Validador local** (heredado de gestion_conocimiento): solo `SELECT`, una sola sentencia, sin `;` encadenados, tablas permitidas = lista blanca, columnas verificadas contra el esquema real, `LIMIT` forzado (tope duro 5.000 filas), timeout de warehouse por sesión.
- **Capa 4 — Transparencia de origen**: cada respuesta muestra (colapsable) la SQL ejecutada, el número de filas y la marca de tiempo de los datos. El usuario puede auditar en el acto.
- **Capa 5 — Redacción bajo contrato + verificador de cifras**: la redacción solo puede usar números presentes en el resultado; un chequeo automático compara los números del texto contra el DataFrame y, si aparece una cifra huérfana, se descarta la redacción y se muestra la tabla con un resumen plantillado (fail-safe sin LLM).
- **Capa 6 — Camino de rechazo**: preguntas fuera de alcance (requisitos de exportación, años fuera de rango, otras bases) reciben una negativa clara con sugerencias de preguntas válidas — regla que su v1 ya tenía en el prompt y que aquí se hace verificable.
- **Capa 7 — Evaluación continua**: `eval/evaluar.py` corre las preguntas doradas (§6.3) contra el sistema completo y calcula exactitud de resultado (comparación de datos, no de texto). **Puerta de release: ≥ 90 % en la suite antes de desplegar a producción; ninguna regresión silenciosa.** Cada corrida queda registrada en telemetría con `VERSION_SEMANTICA`.

---

## 5. Auditoría en Snowflake (su requisito: "todo lo que se consulte, registrado")

Esquema `TELEMETRIA` (extiende el DDL de gestion_conocimiento + el middleware de potencialidad):

- `CHAT_LOG` — una fila por pregunta: `ID` (UUID), `TS TIMESTAMP_TZ`, `SESSION_ID`, `USER_ID`, `PREGUNTA`, `SQL_GENERADA`, `SQL_VALIDADA BOOLEAN`, `EXITO BOOLEAN`, `N_FILAS`, `LATENCIA_ANALYST_MS`, `LATENCIA_SQL_MS`, `LATENCIA_TOTAL_MS`, `PROVEEDOR_REDACCION`, `MODELO_REDACCION`, `COSTO_ESTIMADO_USD`, `INTENTOS`, `ERROR`, `VERSION_APP`, `VERSION_SEMANTICA`.
- `EVENTOS_APP` — eventos de uso (inicio de sesión de app, descargas Excel/PPTX, cambio de proveedor, apertura de /metricas): `TS`, `SESSION_ID`, `EVENTO`, `DETALLES VARIANT`, `VERSION_APP`.
- `FEEDBACK` — pulgar arriba/abajo por respuesta: `TS`, `CHAT_LOG_ID`, `UTIL BOOLEAN`, `COMENTARIO`. Este es su mejor insumo de calidad: preguntas con 👎 alimentan nuevas consultas verificadas.
- Vistas de consumo para `/metricas` y para analistas en Snowsight: `V_CONSULTAS_DIARIAS`, `V_PREGUNTAS_TOP`, `V_TASA_EXITO`, `V_LATENCIAS`, `V_COSTOS_DIARIOS`, `V_FEEDBACK`.
- Reglas: binds parametrizados siempre; cola en memoria + worker único (fail-open, tope de cola con descarte y contador de descartes); **jamás** se registra ninguna clave de API (regla ya escrita en su DDL de gestion). Complemento de plataforma: `CORTEX_ANALYST_USAGE_HISTORY` y el query history de Snowflake para conciliar costos.
- Nota de privacidad: `USER_ID` será un identificador anónimo de sesión mientras no exista SSO; no se capturan datos personales del usuario final.

---

## 6. Modelo semántico de exportaciones v1

### 6.1 Preparación de datos (recomendación fuerte)
`VISTA_EXPORTACIONES_LONG` en formato largo es hostil para texto-a-SQL: obliga a filtros por `VARIABLE_NAME` que los modelos confunden. Propongo materializar **una vista ancha** `VW_EXPORTACIONES` (una fila = año × NIT × posición × país × transporte, columnas = las ~25 variables del diccionario) y apuntar el modelo semántico a esa vista. Si la vista larga es inamovible por gobernanza, el modelo semántico puede describirla, pero la exactitud esperada baja y las consultas verificadas tendrán que cargar el peso. **Decisión suya en §12.**

### 6.2 Contenido del modelo (derivado directo de Definiciones_variables.xlsx)
- Dimensiones con valores enumerados (baja cardinalidad): Año, Continente, Zona geográfica, HUB, Cadena, Tipo, TLC, Medio de transporte, Departamento (origen y "que más exporta").
- Dimensiones no enumerables (ILIKE + sinónimos): País destino, Sector, Subsector, Posición arancelaria y descripción, Razón social, NIT.
- Medidas: `VALOR` (suma de dólares FOB) como métrica canónica; derivadas: participación %, variación interanual, ranking.
- Sinónimos en español por columna (esto decide la mitad de la exactitud; se redactan con su equipo).
- Instrucciones custom: rango temporal 2018–2024; convenciones de "estrella" (agregados por NIT); zonas francas cuentan como destino según la fuente; redondeos.

### 6.3 Suite dorada (mínimo 50 preguntas; primeras 12 de ejemplo)
- ¿Cuánto exportó Colombia en dólares FOB en 2024?
- Top 10 países destino por valor en 2024.
- Exportaciones no mineras por departamento de origen en 2023.
- Variación de las exportaciones de Agroalimentos entre 2022 y 2023.
- Participación del café dentro de las exportaciones no mineras 2024.
- Empresas (razón social) con mayor valor exportado desde Antioquia en 2024.
- Exportaciones a Estados Unidos por medio de transporte, 2024.
- Valor exportado bajo TLC vigente vs sin acuerdo, 2023.
- ¿Qué HUB creció más entre 2021 y 2024?
- Top 5 subpartidas (posición) hacia China en 2024.
- Sector "estrella" más frecuente entre exportadores de Santander.
- Serie anual 2018–2024 del Sistema Moda.
Cada una con su SQL de referencia validada a mano → alimenta el VQR **y** la evaluación.

---

## 7. Experiencia visual (dirección de diseño, no plantilla)

- **Identidad**: institucional ProColombia/MinCIT (logos ya en los repos), pero con carácter propio: paleta anclada en los azules/amarillos institucionales con un acento cálido para los datos; tipografía de display con personalidad para titulares + una sans legible para datos; números tabulares en resultados.
- **Firma visual**: la "tarjeta de respuesta" — cada respuesta del bot es una tarjeta con: redacción breve, cifra protagonista destacada, mini-gráfica Plotly cuando aplique, tabla plegable, chip "Ver SQL", chip de origen ("Snowflake · N filas · vista v1.3"), botones Excel/PPTX y 👍/👎. Esa tarjeta ES el producto; todo lo demás es quieto y disciplinado.
- **Chat**: streaming SSE token a token (sensación de velocidad), historial de sesión, preguntas sugeridas al inicio (las doradas más útiles), estados vacíos y de error escritos con voz institucional clara (qué pasó y qué hacer), accesible (foco visible, contraste AA, responsive a móvil).
- **/metricas**: tarjetas de KPI (consultas, tasa de éxito, latencia p50/p95, costo estimado), serie diaria, top preguntas, feedback reciente; mismo lenguaje visual.

---

## 8. Estándares de ingeniería (los mismos suyos, sin rebajas)

- Python: `ruff` (0 errores) + `mypy`; type hints nativos; docstrings Google (PEP 257); configuración por `dataclass` desde entorno (cero números mágicos); fail-fast en arranque (validar variables y conexión antes de servir); KISS/YAGNI. Refs: https://docs.astral.sh/ruff/ · https://peps.python.org/pep-0257/ · https://fastapi.tiangolo.com
- TypeScript `strict` + ESLint; sin `any` en contratos; tipos generados/espejados de los `schemas.py`.
- Pruebas: pytest (validador, verificador de cifras, telemetría, routers con conexión simulada), Vitest + Testing Library (tarjeta de respuesta, guardia de /metricas), y la suite dorada e2e contra un entorno de staging.
- Pre-commit + GitHub Actions (lint, tipos, tests, build frontend) — su patrón de gestion/geih-analisis.
- Versionado semántico + CHANGELOG; ADRs en `docs/` para D1–D10; conventional commits.
- Exportadores: `openpyxl` (Excel institucional con formato del `excel_institucional.py` del perfilador) y `python-pptx` con plantilla de marca (base: `pptx_digest.py`). Refs: https://openpyxl.readthedocs.io · https://python-pptx.readthedocs.io

---

## 9. Seguridad

- Secretos solo en variables de Railway; `.env.example` documentado; ninguna clave en el repositorio ni en telemetría.
- Snowflake: usuario de servicio, llaves RSA duales (D6), rol de mínimo privilegio, `query_tag='EXPORTBOT'` en toda sesión, network policy si la cuenta lo permite.
- API: rate limiting por sesión (protege el costo por mensaje de Analyst), tamaño máximo de pregunta, CORS cerrado al dominio propio, cabeceras de seguridad estándar, healthcheck sin datos sensibles.
- `/metricas` y `/api/metricas/*` tras token de administrador (D9).
- Advertencia legal de la v1 conservada en la interfaz y en los archivos exportados.

---

## 10. Fases de trabajo (compromisos y criterios de aceptación)

**F0 — Cimientos (esfuerzo estimado: 1 jornada)**
- Entregables: monorepo con estructura de §3; CI verde con lint+tipos+tests vacíos; Dockerfile y railway.toml; usuario de servicio y llaves creadas con el admin de Snowflake; `sql/01_roles.sql` y `02_telemetria_ddl.sql` ejecutados; `.env.example`.
- Aceptación: `GET /api/salud` responde en Railway; una fila de prueba escrita en `TELEMETRIA.EVENTOS_APP` desde el entorno desplegado.

**F1 — Modelo semántico y suite dorada (2–3 jornadas, la fase que más decide la calidad)**
- Entregables: vista ancha creada (o decisión documentada de mantener larga); `modelo_exportaciones.yaml` completo con sinónimos e instrucciones; Semantic View materializada; ≥ 50 preguntas doradas con SQL de referencia; `eval/evaluar.py` funcionando; línea base de exactitud medida y documentada.
- Aceptación: exactitud base reportada por escrito (número, no adjetivo); las 12 preguntas de §6.3 correctas vía API de Analyst en Snowsight/REST.

**F2 — Backend núcleo (2–3 jornadas)**
- Entregables: `/api/chat` con el flujo de 7 capas (§4) y streaming SSE; conexión de llaves duales portada a FastAPI; telemetría con cola+worker escribiendo `CHAT_LOG`; manejo de errores con reintento único informando el error exacto.
- Aceptación: pregunta dorada → respuesta con SQL visible y fila completa en `CHAT_LOG` (latencias y costo incluidos); tests de validador y verificador de cifras en verde; un `DELETE` inyectado en pruebas es rechazado por la capa 3.

**F3 — Frontend de chat (2–3 jornadas)**
- Entregables: app Vite+TS con la tarjeta de respuesta (§7), streaming, historial de sesión, sugerencias iniciales, feedback 👍/👎 conectado a `/api/track`, tema institucional con tokens.
- Aceptación: flujo completo usable en móvil y escritorio desde Railway; Lighthouse accesibilidad ≥ 90; sin llamadas directas del navegador a Snowflake ni a proveedores de IA.

**F4 — /metricas protegida (1 jornada)**
- Entregables: guardia por token; dashboard consumiendo las vistas `V_*`; registro del acceso en `EVENTOS_APP`.
- Aceptación: sin token → 401; con token → KPIs coinciden con consultas manuales en Snowsight.

**F5 — Exportables (1–2 jornadas)**
- Entregables: `/api/exportar/excel` y `/api/exportar/pptx` server-side con branding (pregunta, SQL, tabla, advertencia legal, fecha y versión de datos); botones en la tarjeta; descarga registrada en `EVENTOS_APP`.
- Aceptación: Excel abre sin advertencias y con formato institucional; PPTX usa la plantilla; ambos reproducibles desde el `CHAT_LOG_ID`.

**F6 — Multi-proveedor y modo comparación (1–2 jornadas)**
- Entregables: catálogo de proveedores server-side con fallback a Cortex; selector en la interfaz; vista de comparación (misma SQL, dos redacciones, latencia y costo de cada una); proveedor y modelo registrados por consulta.
- Aceptación: caída simulada del proveedor externo → la respuesta sale igual por Cortex; ninguna clave visible en el cliente ni en logs.

**F7 — Endurecimiento y salida a producción (1–2 jornadas)**
- Entregables: suite dorada ≥ 90 % documentada; prueba de carga básica (20 usuarios concurrentes) con p95 aceptable; revisión de seguridad de §9; RUNBOOK.md (rotación de llaves, actualización del modelo semántico, lectura de costos); versión 2.0.0 etiquetada.
- Aceptación: checklist de §13 completo y firmado por usted.

*Total estimado: 10–15 jornadas efectivas de desarrollo. Si el tiempo aprieta, lo único diferible sin dañar el producto es F6 (comparación) a una v2.1; todo lo demás es núcleo.*

---

## 11. Riesgos y costos de oportunidad (sin anestesia)

- **Disponibilidad de Cortex Analyst en la cuenta/región de ProColombia**: si no está habilitado, F1 se bloquea. Verifíquelo esta semana con el administrador (es una consulta de 10 minutos; no hacerlo puede costarle dos semanas de plan muerto). El plan trae el modo contingencia (D1-A), pero es un plan B con menor precisión, no un destino.
- **Costo por mensaje + warehouse**: sin rate limiting ni monitoreo, un uso viral interno puede sorprender en la factura. Mitigado por §5 y §9, pero exige que usted mire `V_COSTOS_DIARIOS` la primera semana.
- **Datos hasta 2024**: estamos en 2026. Un bot preciso sobre datos viejos genera desconfianza institucional más rápido que un bot impreciso. Defina el ciclo de actualización (¿ETL de dian-exportaciones?) antes del lanzamiento o declare el corte visiblemente en la interfaz (el plan hace lo segundo por defecto).
- **La tabla larga** (§6.1): mantenerla sin vista ancha es la principal amenaza a la meta de precisión.
- **Sinónimos pobres = bot tonto**: la calidad del YAML pesa más que todo el código junto. Reserve tiempo real de su equipo (quien conoce el negocio) en F1; no lo delegue al azar.
- **Factor bus = 1**: documentación (ADRs, RUNBOOK) y CI existen para que esto no dependa de su memoria. No las recorte.

---

## 12. Decisiones que usted debe tomar antes de F1

- ¿Cortex Analyst está habilitado en la cuenta y aprueba el costo por mensaje? (bloqueante)
- ¿Autoriza materializar la vista ancha `VW_EXPORTACIONES` o el modelo se construye sobre la vista larga? (define la exactitud esperable)
- ¿Quién usará la app y con qué control de acceso al chat: abierto interno, clave compartida, o SSO futuro? (afecta F3/F4)
- ¿Tailwind o styled-components? (afecta F3; el plan asume Tailwind)
- ¿Proveedores externos aprobados institucionalmente y con presupuesto de API? (afecta F6; Cortex solo también es un lanzamiento válido)
- ¿Ciclo de actualización de datos post-2024? (afecta el mensaje de corte en la interfaz)

---

## 13. Definición de Hecho — ExportBot 2.0.0

- Exactitud ≥ 90 % en la suite dorada, con el número publicado en `docs/`.
- Toda respuesta muestra su SQL, filas y versión de datos; toda consulta queda en `CHAT_LOG`.
- Autenticación Snowflake por llaves RSA duales; cero contraseñas; cero claves en cliente o repositorio.
- `/metricas` operativa y protegida; exportes Excel y PPTX con branding; feedback capturándose.
- CI verde (lint, tipos, tests); despliegue reproducible en Railway desde `main`; RUNBOOK y ADRs completos; CHANGELOG 2.0.0.

## 14. Referencias
- Cortex Analyst (doc oficial): https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst
- Exactitud y modelo semántico (Snowflake Eng.): https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/ · https://www.snowflake.com/en/blog/engineering/agentic-semantic-model-text-to-sql/
- Semantic Views y monitoreo/costos: https://seemoredata.io/blog/snowflake-cortex-analyst-query-history-monitoring/
- Autenticación por llaves y fin del password single-factor: https://docs.snowflake.com/en/user-guide/key-pair-auth · https://keebo.ai/blog/snowflake-multi-factor-key-pair-authentication/ · https://support.esri.com/en-us/knowledge-base/what-are-esri-s-recommendations-to-mitigate-potential-d-000035129 · https://docs.snowflake.com/en/user-guide/programmatic-access-tokens
- Retiro de Create React App: https://react.dev/blog/2025/02/14/sunsetting-create-react-app · Vite: https://vite.dev
- Railway: https://docs.railway.com · FastAPI: https://fastapi.tiangolo.com · ruff: https://docs.astral.sh/ruff/
- Quickstart Cortex Analyst: https://www.snowflake.com/en/developers/guides/getting-started-with-cortex-analyst/
