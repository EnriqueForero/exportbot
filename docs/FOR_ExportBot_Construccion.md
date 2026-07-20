# FOR Enrique · Construcción de ExportBot 2.0 (aprendizaje en 9 pasos)

**1 · Enfoque y punto de partida.** No empecé por el chat: empecé por el CONTRATO
(config por entorno + guardas + telemetría) y dejé la "inteligencia" como un
proveedor intercambiable. Analogía: primero el chasis y los frenos, después el
motor. Por eso la app arranca incluso SIN credenciales (modo degradado que se
declara en /api/salud): un sistema que explica por qué no puede operar vale más
que uno que muere en silencio.

**2 · Caminos descartados.** (a) LangChain/agentes: capas de indirección que
esconden la SQL — imposible auditar cifra a cifra. (b) Prompt-a-SQL con LLM
genérico (el patrón Frosty de su v1): sin gobierno del esquema, cada modelo
"opina" distinto. (c) pandas+pyarrow en runtime: 200 MB de dependencias para
convertir tuplas en tuplas. (d) Reescribir la Celda B de sus notebooks: su
plantilla ya resolvió (con cicatrices A07.1) lockfiles envenenados y fallos
mudos; tocarla habría sido vandalismo.

**3 · Cómo encajan las piezas.** Semántica (qué significa "exportaciones") →
Analyst (pregunta→SQL) → validador (¿es SOLO lectura y de MI esquema?) →
ejecutor (topes) → redactor (prosa bajo contrato) → verificador (¿cada número
existe en la tabla?) → telemetría (todo queda escrito). El orden no es estético:
cada capa solo confía en lo que la anterior ya garantizó.

**4 · Herramientas y porqués.** Cortex Analyst y no COMPLETE: la precisión vive
en el modelo semántico gobernado, no en el prompt. PAT y llaves RSA: una para
arrancar en 5 minutos, otra para rotar sin caídas. CSS con tokens y no Tailwind:
en un build efímero de Colab, cada dependencia es un punto de falla. SSE por
etapas: la gente perdona 8 segundos si VE el avance.

**5 · Trade-offs.** Prioricé verificabilidad sobre elocuencia (si una cifra no
cuadra, degradamos a plantilla aburrida pero cierta); simplicidad operativa
sobre micro-latencia (un solo contenedor); compatibilidad sobre pureza (mantuve
`facts:` de su generador en vez de migrar a `measures`).

**6 · Errores del camino.** El shell del entorno no expandía llaves `{a,b}` y
mkdir "funcionó" sin crear nada — el fallo apareció DOS comandos después (los
errores viajan). Una prueba de Excel mezclaba dos formas de iterar celdas.
Activar isort a mitad de obra marcó 11 archivos: las reglas de estilo se fijan
el día CERO o se paga interés.

**7 · Trampas para la próxima vez.** "Oculto" no es "seguro" (la /metricas de
modelo_potencialidad lo admitía en un comentario; aquí exige token en tiempo
constante). Un LIMIT que usted no puso es una factura que sí pagará. Y los
notebooks que tocan Drive: patch quirúrgico, jamás reescritura.

**8 · Lo que ve un experto.** Que el reintento le cuenta al Analyst el ERROR
EXACTO (retroalimentación, no ruleta); que la telemetría guarda la VERSIÓN
SEMÁNTICA usada (sin eso, ninguna métrica de exactitud es comparable en el
tiempo); que el fallback termina en una plantilla determinista — el sistema
nunca depende de que un LLM "se porte bien".

**9 · Transferible a cualquier proyecto.** (1) Contratos verificables > promesas
("cero alucinaciones" no existe; "toda cifra proviene del resultado o se
degrada" sí). (2) El conocimiento del dominio en DATOS (YAML), no en código:
así "cambiar de base" es editar un archivo. (3) Toda decisión con costo, por
escrito (DECISIONES.md): dentro de un año, usted-del-futuro lo agradecerá.
