# El archivo frosty_app.py utiliza las funciones y constantes definidas en prompts.py para crear la 
# aplicación web interactiva de ExportBot. Importa la función get_system_prompt() para obtener el 
# mensaje del sistema inicial y lo utiliza para inicializar el historial de mensajes.
#####################################################################################################

# Se importan las bibliotecas necesarias (openai, re, streamlit) y la función get_system_prompt del 
# archivo prompts.py.

from openai import OpenAI  # Importa la biblioteca OpenAI para interactuar con modelos de lenguaje de OpenAI.
import re  # Importa el módulo re para trabajar con expresiones regulares.
import streamlit as st  # Importa la biblioteca Streamlit para crear aplicaciones web interactivas.
from prompts import get_system_prompt  # Importa una función personalizada para obtener el mensaje del sistema.

st.title("🤖 ExportBot 🌎")  # Establece el título de la aplicación web.

# Se inicializa el historial de mensajes del chat. Se crea un cliente de OpenAI utilizando la clave API 
# almacenada en los secretos de Streamlit. Si "messages" no está en el estado de la sesión, se inicializa 
# con el mensaje del sistema obtenido de la función get_system_prompt().

# Inicializa el historial de mensajes del chat.
client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)  # Crea un cliente de OpenAI utilizando la clave API almacenada en los secretos de Streamlit.
if "messages" not in st.session_state:  # Verifica si "messages" no está en el estado de la sesión.
    # El mensaje del sistema incluye información de la tabla, reglas y genera un mensaje de bienvenida para el usuario.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]  # Inicializa "messages" con el mensaje del sistema.

# Se solicita la entrada del usuario y se guarda. Si el usuario ingresa un mensaje en el campo de entrada 
# del chat, se agrega al historial de mensajes.

# Solicita la entrada del usuario y la guarda.
if prompt := st.chat_input():  # Si el usuario ingresa un mensaje en el campo de entrada del chat.
    st.session_state.messages.append({"role": "user", "content": prompt})  # Agrega el mensaje del usuario al historial de mensajes.

# Se muestran los mensajes del chat existentes. Se itera sobre cada mensaje en el historial de mensajes, 
# omitiendo el mensaje del sistema. Se crea un contenedor para cada mensaje según el rol (usuario o 
# asistente) y se escribe el contenido del mensaje en la aplicación web. Si el mensaje contiene resultados
# de una consulta SQL, se muestran en un DataFrame.

# Muestra los mensajes del chat existentes.
for message in st.session_state.messages:  # Itera sobre cada mensaje en el historial de mensajes.
    if message["role"] == "system":  # Omite el mensaje del sistema.
        continue
    with st.chat_message(message["role"]):  # Crea un contenedor para el mensaje según el rol (usuario o asistente).
        st.write(message["content"])  # Escribe el contenido del mensaje en la aplicación web.
        if "results" in message:  # Si el mensaje contiene resultados de una consulta SQL.
            st.dataframe(message["results"])  # Muestra los resultados en un DataFrame.

# Si el último mensaje no es del asistente, se genera una nueva respuesta. Se crea un contenedor vacío para
# actualizar dinámicamente la respuesta. Se llama a la API de OpenAI para generar una respuesta en 
# streaming utilizando el modelo "gpt-3.5-turbo" y los mensajes del historial. A medida que se recibe la 
# respuesta, se agrega el contenido generado a la respuesta y se actualiza el contenedor con la respuesta 
# en formato Markdown. Se crea un nuevo mensaje con la respuesta del asistente. Si se encuentra una consulta 
# SQL en la respuesta (utilizando una expresión regular), se extrae la consulta, se establece una conexión 
# con Snowflake, se ejecuta la consulta y se guardan los resultados en el mensaje. Finalmente, se agrega 
# el mensaje del asistente al historial de mensajes.

# Si el último mensaje no es del asistente, se necesita generar una nueva respuesta.
if st.session_state.messages[-1]["role"] != "assistant":  # Verifica si el último mensaje no es del asistente.
    with st.chat_message("assistant"):  # Crea un contenedor para el mensaje del asistente.
        response = ""  # Inicializa la respuesta como una cadena vacía.
        resp_container = st.empty()  # Crea un contenedor vacío para actualizar dinámicamente la respuesta.
        for delta in client.chat.completions.create(  # Llama a la API de OpenAI para generar una respuesta en streaming.
            model="gpt-3.5-turbo",  # Especifica el modelo de lenguaje a utilizar.
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],  # Prepara los mensajes para la API.
            stream=True,  # Habilita el modo de streaming.
        ):
            response += (delta.choices[0].delta.content or "")  # Agrega el contenido generado a la respuesta.
            resp_container.markdown(response)  # Actualiza el contenedor con la respuesta en Markdown.

        message = {"role": "assistant", "content": response}  # Crea un nuevo mensaje con la respuesta del asistente.
        # Analiza la respuesta en busca de una consulta SQL y la ejecuta si está disponible.
        sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)  # Busca una consulta SQL en la respuesta usando una expresión regular.
        if sql_match:  # Si se encuentra una consulta SQL.
            sql = sql_match.group(1)  # Extrae la consulta SQL.
            conn = st.connection("snowflake")  # Establece una conexión con Snowflake.
            message["results"] = conn.query(sql)  # Ejecuta la consulta SQL y guarda los resultados.
            st.dataframe(message["results"])  # Muestra los resultados en un DataFrame.
        st.session_state.messages.append(message)  # Agrega el mensaje del asistente al historial de mensajes.