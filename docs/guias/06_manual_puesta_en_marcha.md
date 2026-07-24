# 06 · Manual de puesta en marcha — ExportBot 2.0.0
*Manual completo, paso a paso, sin conocimientos previos asumidos. Cada paso termina con una VERIFICACIÓN observable: usted hace X y debe ver Y; si ve otra cosa, el Anexo A le dice qué significa y cómo corregirlo. 2026-07-23.*

---

## Cómo usar este manual
Ejecute las fases **en orden** y no avance si la verificación no da lo esperado. Regla de oro aprendida en este proyecto: *"lo corrí y funcionó" no es evidencia; la evidencia es la salida de la verificación*. Donde diga `<SU_CUENTA>` o similar, reemplace por su valor.

**Los 4 conceptos que necesita (2 minutos):**
1. **Llave privada / pública (RSA):** un par matemático. La *privada* (archivo `.p8`) la guarda usted en secreto y firma; la *pública* se registra en Snowflake para que verifique esas firmas. Nunca viajan juntas.
2. **Secret de Colab:** una cajita cifrada (icono 🔑) donde el notebook lee valores sensibles sin que queden escritos en celdas.
3. **Los dos formatos que causaron el incidente:** Snowflake pide la llave **pública** "sin cabeceras, en una línea"; el Secret de la app lleva la **privada**. Desde rc2 el backend acepta la privada en cualquiera de los formatos habituales, así que este punto ya no puede romperlo — pero entenderlo evita confusiones futuras.
4. **Telemetría:** la base `DB_EXPORTBOT.TELEMETRY` donde la app registra cada pregunta, respuesta y descarga. Es su caja negra de auditoría.

---

## FASE 0 · Actualizar el proyecto a rc2 (5 min)

El rc3 corrige de raíz los incidentes de esta puesta en marcha: acepta su Secret **tal como ya está** y, si algún día un secreto queda ilegible, lo declara al arrancar en `/api/salud` en lugar de fallar en la primera consulta.

1. Descargue `exportbot_v2.0.0.zip` (adjunto a esta conversación).
2. Descomprímalo en su computador.
3. En Google Drive, **renombre** la carpeta actual `exportbot` a `exportbot_rc1_respaldo` (no la borre todavía).
4. Suba la carpeta nueva descomprimida a la misma ubicación, con el nombre `exportbot`.

**Verificación:** en Drive, `ProColombia/exportbot/VERSION` abierto debe decir `2.0.0`.

---

## FASE 1 · Snowflake — registrar la llave pública (10 min) ⚠️ OBLIGATORIA

Su `DESC USER` mostró `RSA_PUBLIC_KEY_FP = null`: Snowflake **no tiene** su llave pública, así que ninguna firma suya puede verificarse todavía. La buena noticia: no necesita openssl ni saber de formatos — la celda siguiente deriva la pública desde el Secret que ya cargó y le imprime el comando completo listo para copiar.

### 1.1 En el notebook de Colab, celda nueva:

```python
from google.colab import userdata
import base64
from cryptography.hazmat.primitives import serialization

raw = base64.b64decode(userdata.get("SF_PRIVATE_KEY_B64_1").strip())
try:
    k = serialization.load_der_private_key(raw, password=None)
except ValueError:
    k = serialization.load_pem_private_key(raw, password=None)
pub = k.public_key().public_bytes(serialization.Encoding.DER,
                                  serialization.PublicFormat.SubjectPublicKeyInfo)
print("Copie y ejecute en Snowsight (una sola línea):\n")
print("ALTER USER SVC_EXPORTBOT SET RSA_PUBLIC_KEY='" + base64.b64encode(pub).decode() + "';")
```

**Verificación:** la celda imprime un comando `ALTER USER ... SET RSA_PUBLIC_KEY='MII...';` de una sola línea larga. Si lanza error → Anexo A.1.

### 1.2 En Snowsight (hoja de trabajo, rol SECURITYADMIN o ACCOUNTADMIN):
Pegue y ejecute el comando impreso. Luego:

```sql
DESC USER SVC_EXPORTBOT;
```

**Verificación:** la fila `RSA_PUBLIC_KEY_FP` ahora muestra `SHA256:...` (ya **no** null) y `HAS_KEYPAIR` = true. Anote esa huella: la comparará en la Fase 3.

---

## FASE 2 · Snowflake — la base de telemetría (10 min)

Su sesión respondió `Database 'DB_EXPORTBOT' does not exist or not authorized`. Antes de "arreglar", diagnostiquemos cuál de los tres mundos es el suyo.

### 2.1 Averiguar qué existe (rol ACCOUNTADMIN):

```sql
SHOW DATABASES LIKE '%EXPORTBOT%';
```

**Árbol de decisión según lo que vea:**
- **Aparece `DB_EXPORTBOT`** → la base existe y su error anterior fue de contexto de rol en esa hoja de trabajo. Salte a 2.3.
- **Aparece solo `BD_EXPORTBOT`** (con B) → usted ejecutó el DDL *viejo* (v1 del repositorio) en lugar del archivo v2 que le entregué. Sin drama: siga a 2.2; conviven sin conflicto y `BD_EXPORTBOT` se puede eliminar después.
- **No aparece ninguna** → el DDL v2 nunca se ejecutó (o se ejecutó en una hoja que falló en silencio). Siga a 2.2.

> **✅ Resultado confirmado en su cuenta (2026-07-24):** apareció solo `BD_EXPORTBOT` (creada 2026-07-23 07:27 por ACCOUNTADMIN). Diagnóstico cerrado: aquella mañana se ejecutó el DDL v1 del repositorio, no el archivo v2. **La corrección es ejecutar 2.2 tal cual** — el aplicativo rc2 NO se toca: código y DDL v2 ya son coherentes entre sí (misma fuente de diseño). La sugerencia de "corregir los nombres en las consultas/app hacia BD_EXPORTBOT.TELEMETRIA" invierte la dirección del arreglo: adaptaría el sistema al artefacto equivocado y perdería RESPUESTA, USER_ID, ENVIRONMENT, EVENT_LOG, DOWNLOAD_EVENT y el bug de versión corregido. Ver Anexo A.11.

### 2.2 Ejecutar el DDL v2 (rol SYSADMIN):
En Snowsight, abra una hoja nueva, seleccione rol **SYSADMIN**, pegue **completo** el contenido del archivo `sql/02_telemetria_v2_ddl.sql` que viene dentro del zip rc2 (carpeta `sql/`), y ejecute **todas** las sentencias (Ctrl+Shift+Enter ejecuta todo; verifique que el panel de resultados no muestre errores en ninguna).

### 2.3 Verificación de la base (cualquier rol administrador):

```sql
SHOW TABLES IN SCHEMA DB_EXPORTBOT.TELEMETRY;
```

**Verificación:** deben listarse **5 tablas**: `CHAT_LOG`, `DOWNLOAD_EVENT`, `EVENT_LOG`, `FEEDBACK`, `UI_EVENT`. Menos de 5 → el DDL no corrió completo; repita 2.2 mirando el panel de errores.

### 2.4 Prueba de mínimo privilegio — versión corregida
⚠️ **Por qué la primera versión de esta prueba dio un falso negativo:** en Snowsight, su usuario humano opera con `SECONDARY ROLES = ALL`, así que aunque el rol *primario* sea `R_EXPORTBOT_APP`, sus roles administradores siguen activos en segundo plano y autorizan el DELETE. La prueba no medía al rol; lo medía a usted. La app real (SVC_EXPORTBOT) no tiene ese problema. Versión que sí mide al rol:

```sql
USE ROLE R_EXPORTBOT_APP; USE SECONDARY ROLES NONE; USE WAREHOUSE APPS_WH;
INSERT INTO DB_EXPORTBOT.TELEMETRY.UI_EVENT (EVENT_TYPE, EVENT_DETAIL, ENVIRONMENT)
  VALUES ('prueba_manual', 'verificación fase 2', 'setup');
SELECT EVENT_TS, EVENT_TYPE, EVENT_DETAIL FROM DB_EXPORTBOT.TELEMETRY.UI_EVENT
  ORDER BY EVENT_TS DESC LIMIT 3;
DELETE FROM DB_EXPORTBOT.TELEMETRY.UI_EVENT;   -- AHORA SÍ debe fallar
USE SECONDARY ROLES ALL;                        -- restaura su sesión normal
```

**Verificación:** INSERT y SELECT funcionan; el **DELETE falla** con *Insufficient privileges*. Confirmación adicional de que el rol está limpio: `SHOW GRANTS TO ROLE R_EXPORTBOT_APP;` no debe listar `DELETE`, `UPDATE`, `TRUNCATE` ni `OWNERSHIP` sobre TELEMETRY. Si el DELETE aún funciona con `SECONDARY ROLES NONE` → Anexo A.2.

---

## FASE 3 · Colab — relanzar y comprobar la llave (10 min)

1. En el notebook, ejecute la celda `detener()` si existe (o *Entorno de ejecución → Reiniciar*), y vuelva a correr las celdas **en orden** desde la Celda A. No hay nada que editar: la Celda A del rc2 ya trae la configuración correcta.
2. Espere el veredicto de la celda de lanzamiento (URL pública verificada ✅).

### 3.1 Verificación de salud (celda nueva):

```python
import json, urllib.request
print(json.dumps(json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/salud")), indent=2, ensure_ascii=False))
```

**Verificación — los 7 campos que importan:**
- `"estado": "ok"`
- `"auth_snowflake": "keypair"`
- `"usuario_snowflake": "SVC_EXPORTBOT"` ← **nuevo en rc3**; si muestra otro usuario (p. ej. la cuenta compartida), ahí está su 401: corrija el Secret `SF_USER` (Anexo A.12)
- `"cuenta"`: el identificador que usa para conectarse (p. ej. `my17686.us-east-2.aws`)
- `"llave_rsa": "legible (SHA256:....)"` ← **nuevo en rc2**; si dice `ILEGIBLE`, el propio mensaje explica qué corregir (Anexo A.3)
- La huella dentro de `llave_rsa` es **idéntica** a la `RSA_PUBLIC_KEY_FP` que anotó en la Fase 1.2. Idénticas = la llave que firma es la que Snowflake espera. Distintas → Anexo A.4.
- `"telemetria": true` y `"entorno": "colab"`

### 3.2 El log ya no debe quejarse (celda nueva):

```python
logs("backend", n=30)
```

**Verificación:** NO deben aparecer líneas `Fallo de conexión` ni `MalformedFraming`. Debe verse `Telemetría activa hacia DB_EXPORTBOT.TELEMETRY`.

---

## FASE 4 · La primera consulta de verdad (5 min)

1. Abra la **URL pública** que imprimió el notebook.
2. Haga clic en la consulta de referencia *"¿Cuánto exportó Colombia en USD FOB en 2025?"*.
3. Observe las etapas: *Interpretando… → SQL validada → Consultando… → Redactando…* y la respuesta final con cifras y tabla.
4. Haga una segunda pregunta (*"Top 5 empresas exportadoras de Antioquia en 2025"*) y **descargue el Excel** de esa tarjeta.
5. Marque 👍 en una de las dos respuestas.

**Verificación:** dos respuestas con cifras (no el banner rojo). Si vuelve el banner → el mensaje del rc2 ya será específico (p. ej. *"Cortex Analyst no respondió: Llave privada ilegible: …"* o `HTTP 401`); búsquelo en el Anexo A.

---

## FASE 5 · La caja negra registró todo (5 min, en Snowsight)

```sql
-- (a) Requests HTTP del middleware:
SELECT EVENT_TS, METHOD, ENDPOINT, RESPONSE_STATUS, RESPONSE_TIME_MS, ENVIRONMENT
FROM DB_EXPORTBOT.TELEMETRY.EVENT_LOG ORDER BY EVENT_TS DESC LIMIT 10;

-- (b) Rastro completo pregunta → SQL → respuesta:
SELECT TS, LEFT(PREGUNTA,50) PREGUNTA, EXITO, CIFRAS_VERIFICADAS, RESPUESTA_DEGRADADA,
       LEFT(RESPUESTA,80) RESPUESTA, VERSION_APP, ENVIRONMENT
FROM DB_EXPORTBOT.TELEMETRY.CHAT_LOG ORDER BY TS DESC LIMIT 5;

-- (c) Versión real (el bug corregido):
SELECT EVENT_TS, EVENT_TYPE, APP_VERSION FROM DB_EXPORTBOT.TELEMETRY.UI_EVENT
ORDER BY EVENT_TS DESC LIMIT 5;

-- (d) La descarga, ligada a su chat:
SELECT EVENT_TS, DOWNLOAD_TYPE, FILE_NAME, N_ROWS, CHAT_LOG_ID
FROM DB_EXPORTBOT.TELEMETRY.DOWNLOAD_EVENT ORDER BY EVENT_TS DESC LIMIT 3;

-- (e) Su pulgar arriba:
SELECT TS, UTIL, CHAT_LOG_ID FROM DB_EXPORTBOT.TELEMETRY.FEEDBACK
ORDER BY TS DESC LIMIT 3;
```

**Verificación:** (a)–(e) devuelven filas; en (b) `EXITO=TRUE`, `RESPUESTA` poblada, `ENVIRONMENT='colab'`; en (c) `APP_VERSION='2.0.0'` (jamás vacío).

---

## FASE 6 · El gate de calidad: exactitud ≥ 90 % (15 min)

Con la app corriendo, en una celda nueva del notebook:

```python
import subprocess, glob
raiz = glob.glob("/content/app/*/eval")[0].rsplit("/eval", 1)[0]
r = subprocess.run(["python", "eval/evaluar.py", "--url", "http://127.0.0.1:8000"],
                   cwd=raiz, capture_output=True, text=True)
print("returncode:", r.returncode)
print("── stdout ──"); print(r.stdout[-3500:] or "(vacío)")
print("── stderr ──"); print(r.stderr[-1500:] or "(vacío)")
```

*(La versión anterior solo imprimía stdout: si el script fallaba, el error iba a stderr y usted veía "nada". Regla general: todo subprocess se lee con returncode + stdout + stderr.)*

**Verificación:** el reporte final indica el porcentaje de las 12 preguntas doradas. **≥ 90 %** = ExportBot queda declarado apto y pasamos a Railway (guía 05). **< 90 %** = péguemelo completo: la corrección casi siempre es una verified query o una regla de `custom_instructions`, no código. *(Recordatorio pendiente de la Fase anterior: confirme en Snowsight cuántas verified queries tiene realmente `SV_EXPORTACIONES` — su export mostraba 8, su narración 12; el eval merece correr contra la vista completa.)*

---

## FASE 7 · Checklist de cierre

- [ ] `VERSION` en Drive = 2.0.0
- [ ] `RSA_PUBLIC_KEY_FP` ≠ null y **coincide** con la huella de `/api/salud`
- [ ] `SHOW TABLES` en TELEMETRY = 5 tablas; DELETE del rol de la app **falla**
- [ ] `/api/salud`: estado ok · keypair · llave legible · telemetría true · entorno colab
- [ ] Dos consultas reales respondidas + Excel descargado + 👍
- [ ] Las 5 consultas de la Fase 5 devuelven filas coherentes
- [ ] Eval ≥ 90 % (o el reporte de fallos enviado para ajuste)

Cumplido esto, el pendiente restante es UNO: Railway con `ARRANQUE_ESTRICTO=true` (guía 05 §2–§4) — y allí el fail-fast del rc2 hará su trabajo: si un secreto llega mal a producción, el deploy muere gritando la causa en vez de sonreír y fallar después.

---

## FASE 8 · Decisiones de cuenta: usuario de Railway, orden y retiro del legado

### 8.1 · Qué usuario de servicio usa Railway — decisión con veredicto
Existen dos candidatos: `SVC_EXPORTBOT` (creado para esta app, llave RSA ya registrada, `DEFAULT_ROLE = R_EXPORTBOT_APP`) y `USER_SERVICE_ANALITICA` (cuenta compartida del equipo con roles de varias apps: APP_CITI, APP_BOLSILLO, APP_MODELO_EXPO…).

**Veredicto: use `SVC_EXPORTBOT` en Railway.** No es una preferencia estética; hay un argumento técnico decisivo: la API REST de Cortex Analyst autentica el JWT del usuario y **opera con el rol por defecto de ese usuario** (el cuerpo del mensaje no admite un parámetro de rol — verificado en el cliente del backend y en el ejemplo oficial de Snowflake). Con `SVC_EXPORTBOT`, el default ya es `R_EXPORTBOT_APP` y todo cuadra sin tocar nada. Con `USER_SERVICE_ANALITICA`, Analyst correría con el rol por defecto de esa cuenta (el de otra app), y "arreglarlo" cambiándole el default rompería las demás aplicaciones que dependen de él. A eso se suman el radio de explosión (una llave filtrada compromete todas las apps que comparten la cuenta) y la rotación acoplada (rotar para ExportBot obliga a coordinar con todas).

**⚠️ NO ejecute** `ALTER USER USER_SERVICE_ANALITICA SET DEFAULT_ROLE = R_EXPORTBOT_APP;` aunque se lo hayan sugerido: cambia el rol con el que arrancan las sesiones de TODAS las apps que usan esa cuenta.

### 8.2 · Limpieza del GRANT ya ejecutado
Se otorgó `R_EXPORTBOT_APP` a `USER_SERVICE_ANALITICA`. Con la decisión 8.1, ese grant sobra; por higiene de mínimo privilegio, revóquelo:

```sql
USE ROLE SECURITYADMIN;
REVOKE ROLE R_EXPORTBOT_APP FROM USER USER_SERVICE_ANALITICA;
```

*(Solo si el equipo decidiera formalmente lo contrario — usar la cuenta compartida — se conserva el grant, se registra una llave propia en ese usuario y se acepta por escrito el trade-off de Analyst con rol ajeno. No lo recomiendo.)*

### 8.3 · Endurecimiento opcional de SVC_EXPORTBOT (30 segundos)
Su `DESC USER` mostró `DEFAULT_SECONDARY_ROLES = ["ALL"]`. Con un solo rol otorgado es inocuo, pero cerrar la puerta cuesta una línea y evita sorpresas si algún día alguien le otorga otro rol:

```sql
USE ROLE SECURITYADMIN;
ALTER USER SVC_EXPORTBOT SET DEFAULT_SECONDARY_ROLES = ();
```

### 8.4 · Retiro de `BD_EXPORTBOT` (v1) — al final, no ahora
La base v1 no contiene datos reales (la app nunca logró conectarse; solo hubo inserciones de prueba, ya borradas). Aún así, no se quema la nave antes de cruzar: **solo después** de que la Fase 5 muestre filas reales en `DB_EXPORTBOT.TELEMETRY` con `ENVIRONMENT='colab'`, ejecute:

```sql
USE ROLE ACCOUNTADMIN;
DROP DATABASE BD_EXPORTBOT;   -- v1 legada; el diseño vigente es DB_EXPORTBOT.TELEMETRY
```

**Verificación:** `SHOW DATABASES LIKE '%EXPORTBOT%';` devuelve una sola fila: `DB_EXPORTBOT`.

---

## ANEXO A · Diccionario de errores (síntoma → significado → corrección)

**A.1 · La celda de la Fase 1.1 lanza `ValueError`** → el Secret no contiene una llave privada utilizable. Regenérelo: si conserva el archivo `.p8`, en Colab suba el archivo y ejecute `import base64; print(base64.b64encode(open('rsa_exportbot_1.p8','rb').read()).decode())`, copie la línea al Secret. Si NO conserva el `.p8`, genere un par nuevo (guía 04 §0.2) y repita Fases 1–3.

**A.2 · El DELETE de 2.4 NO falla** → el rol tiene privilegios de más. Ejecute `SHOW GRANTS TO ROLE R_EXPORTBOT_APP;`, identifique cualquier `DELETE`/`OWNERSHIP`/`ALL` sobre TELEMETRY y revóquelo; lo esperado es solo USAGE (db/schema) + INSERT + SELECT sobre las tablas.

**A.3 · `/api/salud` dice `llave_rsa: ILEGIBLE: <motivo>`** → el propio motivo es la instrucción (está redactado para eso). Corrija el Secret según el texto y reinicie el lanzamiento. Este mensaje sustituye al viejo "Error interno" — ya no hay que ir al log a cazar tracebacks.

**A.4 · Huella de `/api/salud` ≠ `RSA_PUBLIC_KEY_FP`** → firma una llave distinta de la registrada (típico tras regenerar pares). Repita la Fase 1.1–1.2 con el Secret vigente: la celda deriva la pública correcta *desde ese Secret*, imposible desalinearse.

**A.5 · Banner con `HTTP 401` en el chat** → JWT bien firmado pero rechazado: (i) huella desalineada → A.4; (ii) `SF_USER` distinto de `SVC_EXPORTBOT`; (iii) `SF_ACCOUNT` con formato no válido para REST — use el identificador con el que entra al navegador (`https://<ESTO>.snowflakecomputing.com`).

**A.6 · `Database 'DB_EXPORTBOT' does not exist or not authorized`** → Fase 2.1: o la base no existe (ejecute 2.2) o su hoja está en un rol sin visibilidad (cambie el rol del worksheet arriba a la derecha).

**A.7 · `Requested role '...' is not assigned to the executing user`** → ese rol no está otorgado a SU usuario humano; ejecútese el `GRANT ROLE ... TO USER` con SECURITYADMIN (ya lo hizo para R_EXPORTBOT_APP; aplica igual a cualquier otro).

**A.8 · `ModuleNotFoundError: No module named 'config'` en celdas de diagnóstico** → la ruta local real anida la carpeta del proyecto (`/content/app/exportbot/backend`, no `/content/app/backend`). Use la forma robusta: `from pathlib import Path; import sys; sys.path.insert(0, str(next(Path('/content/app').glob('**/backend/main.py')).parent))`.

**A.9 · `MalformedFraming` en logs viejos** → era el rc1 leyendo un Secret en formato DER-b64. Resuelto estructuralmente en rc2; si lo ve con rc2, no está corriendo rc2 (verifique Fase 0).

**A.10 · El notebook se queda "instalando" eternamente** → caso histórico del b1 (lockfiles con espejo privado), resuelto desde b2; si reapareciera, la Celda A trae `REPARAR_LOCKFILES=True` que lo sanea.

**A.12 · `JWT token is invalid` (401) con `llave_rsa: legible` y huella IDÉNTICA a `DESC USER`** → la llave es correcta pero el token declara una identidad que no es su dueña. Como la cuenta sale del mismo host que responde, el sospechoso dominante es el Secret `SF_USER` apuntando a otro usuario (p. ej. la cuenta compartida del equipo). Diagnóstico en 20 segundos, celda de Colab:

```python
from google.colab import userdata
def s(k):
    try: return userdata.get(k)
    except Exception: return None
print("SF_ACCOUNT =", repr(s("SF_ACCOUNT")))
print("SF_USER    =", repr(s("SF_USER")))       # esperado: 'SVC_EXPORTBOT' exacto, sin espacios
print("SF_ROLE    =", repr(s("SF_ROLE")))       # esperado: 'R_EXPORTBOT_APP'
print("¿Secret SF_PRIVATE_KEY_B64_2 definido?:", bool(s("SF_PRIVATE_KEY_B64_2")))
```

Corrija el Secret que no coincida y relance. Nota sobre la llave 2: si ese Secret existe pero `RSA_PUBLIC_KEY_2` en Snowflake es null, **bórrelo por ahora** — el failover a una llave sin pública registrada solo fabrica más 401. Desde rc3, `/api/salud` muestra `usuario_snowflake`, `cuenta` y `llave_rsa_2` para que este desajuste sea visible sin abrir los Secrets.

**A.13 · El DELETE de la prueba 2.4 "funciona" cuando no debería** → si fue en Snowsight sin `USE SECONDARY ROLES NONE`, es un falso negativo: sus roles administradores seguían activos en segundo plano (ver 2.4 corregida). Solo si falla también con `SECONDARY ROLES NONE` hay privilegios de más en el rol → A.2.

**A.11 · Una IA de la cuenta (Coco/Copilot) sugiere "corregir los nombres" hacia `BD_EXPORTBOT.TELEMETRIA.EVENTOS_APP`** → sus *hechos* son correctos (eso es lo que existe hoy en la cuenta), pero su *dirección* está invertida: esa IA ve el estado, no el contrato del proyecto. La base v1 es el artefacto ejecutado por error; el diseño vigente (estándar GIC 2026-05-13 + requisitos de auditoría de ExportBot) es `DB_EXPORTBOT.TELEMETRY`, y el código rc2 ya está alineado a él. La corrección siempre es ejecutar el DDL v2 (Fase 2.2), nunca reescribir la app hacia el esquema viejo. Use las IAs de la cuenta para *consultar estado* (SHOW/DESC, privilegios) — son excelentes en eso — y traiga las decisiones de rumbo al contrato del proyecto. Y jamás acepte de ellas cambios de `DEFAULT_ROLE` en cuentas compartidas (ver 8.1).

## ANEXO B · Comandos de llaves por sistema operativo (referencia)

*Generar el par (una vez):*
- Windows (PowerShell con OpenSSL instalado) / macOS / Linux:
  `openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out rsa_exportbot_1.p8 -nocrypt`
  `openssl rsa -in rsa_exportbot_1.p8 -pubout -out rsa_exportbot_1.pub`

*Secret de Colab (la PRIVADA, archivo completo):*
- Linux: `base64 -w0 rsa_exportbot_1.p8`
- macOS: `base64 -i rsa_exportbot_1.p8 | tr -d '\n'`
- Windows PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("rsa_exportbot_1.p8"))`
- *(Desde rc2, también se acepta el cuerpo del PEM sin cabeceras — pero use el formato completo por higiene.)*

*Para Snowflake (la PÚBLICA, sin cabeceras, una línea):* no lo haga a mano — use la celda de la Fase 1.1, que lo imprime listo. Referencia manual: Linux/macOS `grep -v '^-----' rsa_exportbot_1.pub | tr -d '\n'`; PowerShell `(Get-Content rsa_exportbot_1.pub | Where-Object {$_ -notmatch '-----'}) -join ''`.
