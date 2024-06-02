# El archivo prompts.py contiene la configuración y la generación del mensaje del sistema para ExportBot. 
# Define constantes, consultas SQL y funciones para obtener el contexto de la tabla y el mensaje del 
# sistema completo.

import streamlit as st

# Se definen constantes para el nombre de la aplicación, la base de datos, el esquema, el nombre de la 
# tabla, la tabla de definiciones, las variables únicas, los años inicial y final

NOMBRE_APLICATIVO = "APLICATIVO_CHATBOT_EXPORTACIONES"
DATABASE_SNOWFLAKE = f'BD_{NOMBRE_APLICATIVO}'
SCHEMA_SNOWFLAKE = f'SCHEMA_{NOMBRE_APLICATIVO}'
TABLE_NAME = "VISTA_EXPORTACIONES_LONG"
TABLA_DEFINICIONES = "VISTA_DEFINICIONES_VARIABLES"
VARIABLES_UNICAS = "Unique Values - Opciones de selección"
AÑO_INICIAL = 2018
AÑO_FINAL = 2024

# Se define la ruta del esquema y el nombre completo de la tabla utilizando las constantes definidas 
# anteriormente
SCHEMA_PATH = st.secrets.get("SCHEMA_PATH", f"{DATABASE_SNOWFLAKE}.{SCHEMA_SNOWFLAKE}")
QUALIFIED_TABLE_NAME = f"{SCHEMA_PATH}.{TABLE_NAME}"

# Se define una descripción detallada de la tabla, incluyendo información sobre las estadísticas de 
# exportaciones, las variables disponibles y las preguntas que los usuarios pueden hacer.
TABLE_DESCRIPTION = f"""
Esta tabla contiene estadísticas de exportaciones de bienes de Colombia al mundo, 
con información anual desde el año {AÑO_INICIAL} hasta {AÑO_FINAL}.
Incluye variables como: país de destino, departamento de origen,  
modo de transporte, bandera, subpartida arancelaria, kilos brutos, kilos netos y valor 
FOB en dólares estadounidenses.
Los usuarios pueden hacer preguntas sobre exportaciones por año, país de destino, 
departamento de origen, posición arancelaria, cadena productiva, sector, subsector, 
tipo de exportación, tratado de libre comercio, medio de transporte, entre otras variables disponibles.
La tabla también permite identificar el departamento, cadena productiva, sector, 
subsector y tipo de exportación que más exporta cada empresa identificada por su NIT y su razón social.
"""
# This query is optional if running ExportBot on your own table, especially a wide table.
# Since this is a deep table, it's useful to tell ExportBot what variables are available.
# Similarly, if you have a table with semi-structured data (like JSON), it could be used to provide hints on available keys.
# If altering, you may also need to modify the formatting logic in get_table_context() below.
# METADATA_QUERY = f"SELECT VARIABLE_NAME, DEFINITION FROM {SCHEMA_PATH}.{TABLA_DEFINICIONES};"

# Define una consulta SQL llamada METADATA_QUERY utilizando una cadena de texto con formato (f-string)
# La consulta selecciona las columnas VARIABLE_NAME, DEFINITION y UNIQUE_VALUES de la tabla especificada por {SCHEMA_PATH}.{TABLA_DEFINICIONES}
# VARIABLES_UNICAS es una variable que se interpola en la consulta y se utiliza como alias para la columna UNIQUE_VALUES
METADATA_QUERY = f"""
    SELECT VARIABLE_NAME, DEFINITION, "{VARIABLES_UNICAS}" as UNIQUE_VALUES
    FROM {SCHEMA_PATH}.{TABLA_DEFINICIONES};
"""

# Se define el mensaje del sistema (GEN_SQL) que se utilizará para inicializar ExportBot. Este mensaje 
# incluye instrucciones sobre cómo actuar como un experto en SQL, las reglas críticas que debe seguir 
# (como envolver el código SQL generado en un bloque de código Markdown, limitar el número de respuestas 
# a 10, usar coincidencia difusa para las cláusulas WHERE de texto/cadena, generar un único código SQL 
# único, usar solo las columnas proporcionadas, no anteponer números a las variables SQL, usar comillas 
# dobles alrededor de los nombres de columna, usar solo los valores únicos especificados para cada columna,
# no responder preguntas sobre requisitos de exportaciones) y cómo presentarse e interactuar con el usuario.

GEN_SQL = """
You will be acting as an AI SQL Expert named ExportBot.
Your goal is to give only one correct and the best executable sql query to users.
Será penalizado si da más de una sql query. Igual será penalizado y no da la mejor SQl Query. 
Recibirá una recompensa generoa por dar el mejor query en SQL de Snowflake basado en la tabla. 
You will be replying to users who will be confused if you don't respond in the character of ExportBot.
You are given one table, the table name is {QUALIFIED_TABLE_NAME}, the columns are in <columns> tag.
The user will ask questions, for each question you should respond and include a sql query based on the question and the table. 
Preséntese siempre en idioma español. 

{context}

Here are 10 critical rules for the interaction you must abide:
<rules>
1. You MUST MUST wrap the generated sql code within ``` sql code markdown in this format e.g
```sql
(select 1) union (select 2)
```
2. If I don't tell you to find a limited set of results in the sql query or question, you MUST limit the number of responses to 10.
3. Text / string where clauses must be fuzzy match e.g ilike %keyword%
4. Make sure to generate a single unique snowflake sql code, not multiple. Only one sql code, the best. 
5. You should only use the table columns given in <columns>, and the table {QUALIFIED_TABLE_NAME}, you MUST NOT hallucinate about the table names
6. DO NOT put numerical at the very front of sql variable.
7. Always use double quotes around column names in the SQL queries to preserve their exact capitalization, e.g., "Tipo" instead of TIPO or Tipo.
8. When generating SQL queries, only use the unique values specified for each column in the metadata. Do not invent or assume values that are not explicitly listed.
9. No responda preguntas sobre requisitos de exportaciones. Sólo responda preguntas relacionadas con las cifras y la base de datos. 
</rules>

Don't forget to use "ilike %keyword%" for fuzzy match queries (especially for variable_name column)
and wrap the generated sql code with ``` sql code markdown in this format e.g:
```sql
(select 1) union (select 2)
```

For each question from the user, make sure to include a query in your response.

Now to get started, please briefly introduce yourself como un experto en responder preguntas sobre cifras de exportaciones de bienes de Colombia, 
describe the table at a high level, and share the available metrics in 2-3 sentences.
Then provide 3 example questions using bullet points.
Indique las preguntas a hacer deben ser claras y concretas de acuerdo a lo que se requiere.
Recomiende verificar los resultados. "La Inteligencia Artificial puede cometer errores. Comprueba la información importante".
"""

# Se define la función get_table_context() que se utiliza para obtener el contexto de la tabla. Esta 
# función toma el nombre de la tabla, la descripción de la tabla y una consulta de metadatos opcional. 
# Realiza una consulta a la base de datos para obtener los nombres y tipos de datos de las columnas de 
# la tabla y los formatea en un string. Luego, combina esta información con la descripción de la tabla 
# y, opcionalmente, con los metadatos de las variables disponibles obtenidos de la consulta METADATA_QUERY. Retorna el contexto formateado.

# Define una función llamada get_table_context que toma tres parámetros: table_name, table_description y metadata_query
# La función está decorada con @st.cache_data, lo que indica que los resultados de la función se almacenarán en caché para evitar llamadas repetidas a la base de datos
# El parámetro show_spinner muestra un mensaje de carga mientras se ejecuta la función
@st.cache_data(show_spinner="Loading 🤖 ExportBot 🌎 context...")
def get_table_context(table_name: str, table_description: str, metadata_query: str = None):
    # Divide el table_name en partes utilizando el separador "." y se guarda en la variable table
    table = table_name.split(".")
    # Establece una conexión con Snowflake utilizando st.connection("snowflake") y se guarda en la variable conn
    conn = st.connection("snowflake")
    
    # Ejecuta una consulta SQL para obtener los nombres de columna y los tipos de datos de la tabla especificada
    # La consulta utiliza las partes del nombre de la tabla (table[0], table[1], table[2]) para construir la consulta
    # El parámetro show_spinner=False evita mostrar un spinner de carga durante la consulta
    columns = conn.query(f"""
        SELECT COLUMN_NAME, DATA_TYPE FROM {table[0].upper()}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{table[1].upper()}' AND TABLE_NAME = '{table[2].upper()}'
        """, show_spinner=False,
    )
    
    # Formatea el resultado de la consulta de columnas en una cadena de texto legible
    # Utiliza una comprensión de lista para iterar sobre los nombres de columna y los tipos de datos,
    # y crea una cadena de texto con el formato - **"nombre_columna"**: tipo_dato para cada columna
    # Las cadenas de texto resultantes se unen utilizando el separador de línea (\n)
    columns = "\n".join(
        [
            f'- **"{columns["COLUMN_NAME"][i]}"**: {columns["DATA_TYPE"][i]}'
            for i in range(len(columns["COLUMN_NAME"]))
        ]
    )
    
    # Crea una cadena de texto llamada context que incluye información sobre el nombre de la tabla, la descripción de la tabla y las columnas de la tabla
    # El nombre de la tabla se une utilizando el separador "." ('.join(table)')
    # La descripción de la tabla se envuelve en etiquetas <tableDescription> y </tableDescription>
    # Las columnas de la tabla se envuelven en etiquetas <columns> y </columns>, y se insertan en la cadena de texto utilizando las variables columns
    context = f"""
Here is the table name {'.'.join(table)}

<tableDescription>{table_description}</tableDescription>

Here are the columns of the {'.'.join(table)}

<columns>\n\n{columns}\n\n</columns>
    """
    
    # Si se proporciona una consulta de metadatos (metadata_query), se ejecuta esa consulta utilizando conn.query(metadata_query, show_spinner=False)
    # y se guarda el resultado en la variable metadata
    if metadata_query:
        metadata = conn.query(metadata_query, show_spinner=False)
        
        # Formatea el resultado de la consulta de metadatos en una cadena de texto legible
        # Utiliza una comprensión de lista para iterar sobre los nombres de las variables, las definiciones y los valores únicos,
        # y crea una cadena de texto con el formato - **nombre_variable**: definición\n  Unique Values: valores_unicos para cada variable
        # Las cadenas de texto resultantes se unen utilizando el separador de línea (\n)
        metadata = "\n".join(
            [
                f"- **{metadata['VARIABLE_NAME'][i]}**: {metadata['DEFINITION'][i]}\n"
                f"  Unique Values: {metadata['UNIQUE_VALUES'][i] or 'N/A'}"
                for i in range(len(metadata["VARIABLE_NAME"]))
            ]
        )
        
        # Agrega la información de las variables disponibles al context existente
        context = context + f"\n\nAvailable variables by VARIABLE_NAME:\n\n{metadata}"
    
    # Devuelve la cadena de texto context que contiene la información formateada sobre la tabla y las variables disponibles
    return context

# Se define la función get_system_prompt() que llama a la función get_table_context() con los parámetros 
# necesarios y devuelve el mensaje del sistema completo utilizando el formato definido en GEN_SQL.
def get_system_prompt():
    # Llama a la función get_table_context con los parámetros QUALIFIED_TABLE_NAME, TABLE_DESCRIPTION y METADATA_QUERY,
    # y guarda el resultado en la variable table_context
    table_context = get_table_context(
        table_name=QUALIFIED_TABLE_NAME,
        table_description=TABLE_DESCRIPTION,
        metadata_query=METADATA_QUERY
    )
    
    # Devuelve el resultado de formatear la cadena de texto GEN_SQL utilizando el table_context y QUALIFIED_TABLE_NAME como argumentos
    return GEN_SQL.format(context=table_context, QUALIFIED_TABLE_NAME=QUALIFIED_TABLE_NAME)

# do `streamlit run prompts.py` to view the initial system prompt in a Streamlit app
# Esta sección se ejecuta solo si el script se ejecuta directamente (no se importa como módulo)
if __name__ == "__main__":
    # Muestra un encabezado con el texto "System prompt for ExportBot" utilizando st.header()
    st.header("System prompt for ExportBot")
    
    # Llama a la función get_system_prompt() y su resultado se muestra en formato Markdown utilizando st.markdown()
    st.markdown(get_system_prompt())
