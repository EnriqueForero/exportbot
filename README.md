# 🤖 ExportBot 🌎

ExportBot es una aplicación web interactiva que permite a los usuarios interactuar con un asistente de IA experto en SQL para obtener información sobre estadísticas de exportaciones de bienes de Colombia. El asistente tiene acceso a una tabla específica de una base de datos Snowflake y puede generar y ejecutar consultas SQL basadas en las preguntas de los usuarios.

## 📋 Requisitos

- Python 3.7 o superior
- Bibliotecas:
  - openai
  - streamlit
  - snowflake-connector-python

## 🚀 Instalación

1. Clona este repositorio:

```bash
git clone https://github.com/EnriqueForero/exportbot.git
cd export-bot
```

2. Crea y activa un entorno virtual (opcional pero recomendado):

```bash
python -m venv venv
source venv/bin/activate  # en Windows: venv\Scripts\activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

4. Configura las variables de entorno:

- Crea un archivo `.env` en la raíz del proyecto.
- Agrega la siguiente línea al archivo `.env` con tu clave API de OpenAI:

```
OPENAI_API_KEY=tu-clave-api-openai
```

5. Configura las credenciales de Snowflake en Streamlit Secrets:

- En tu aplicación de Streamlit, ve a "Settings" > "Secrets".
- Agrega las siguientes claves y valores:
  - `SNOWFLAKE_ACCOUNT`: Tu nombre de cuenta de Snowflake.
  - `SNOWFLAKE_USER`: Tu nombre de usuario de Snowflake.
  - `SNOWFLAKE_PASSWORD`: Tu contraseña de Snowflake.
  - `SNOWFLAKE_WAREHOUSE`: El nombre del almacén de datos (warehouse) de Snowflake.
  - `SNOWFLAKE_DATABASE`: El nombre de la base de datos de Snowflake.
  - `SNOWFLAKE_SCHEMA`: El nombre del esquema de Snowflake.

## 🔧 Configuración

- Revisa y actualiza las constantes en el archivo `prompts.py` según tu configuración de Snowflake y los requisitos de tu aplicación.

## 💻 Uso

1. Inicia la aplicación de Streamlit:

```bash
streamlit run frosty_app.py
```

2. Abre tu navegador web y ve a la URL proporcionada por Streamlit (por defecto, `http://localhost:8501`).

3. Interactúa con ExportBot haciendo preguntas sobre estadísticas de exportaciones de bienes de Colombia. El asistente generará y ejecutará consultas SQL basadas en tus preguntas y mostrará los resultados en la aplicación web.

## 📂 Estructura del proyecto

- `frosty_app.py`: Archivo principal de la aplicación web ExportBot.
- `prompts.py`: Configuración y generación del mensaje del sistema para ExportBot.
- `funciones.py`: funciones para darle formato al documento en word a exportar.
- `README.md`: Documentación del proyecto.
- `requirements.txt`: Lista de dependencias del proyecto.

## 🤝 Contribución

Las contribuciones son bienvenidas. Si encuentras algún problema o tienes alguna sugerencia de mejora, por favor, abre un issue o envía un pull request.

## 📄 Fuente

La programación inicial de este proyecto fue tomada de https://quickstarts.snowflake.com/guide/frosty_llm_chatbot_on_streamlit_snowflake/#0 
Aquí se hicieron modificaciones para cambiar las bases de datos a utilizar y el enfoque. 
