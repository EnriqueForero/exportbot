# 05 · Guía Railway — ExportBot 2.0.0 (producción)
*Todo lo que ocurre en Railway. Prerrequisito: la §6 de la guía 04 (eval ≥ 90 % en Colab) — desplegar a producción algo que no pasó el gate es invertir el orden de la evidencia. 2026-07-23.*

---

## §1 · Origen del despliegue
Vía recomendada (ya preparada en el repo): publique el rc1 en GitHub con `notebooks/Publicar_GitHub.ipynb` y cree el servicio Railway **desde el repositorio** (Deploy from GitHub repo). El proyecto trae `Dockerfile` y `railway.toml` verificados; Railway detecta ambos y no hay nada que configurar de build. Alternativa temporal: Railway CLI con `railway up` desde la carpeta del rc1 — funciona, pero deja el despliegue sin trazabilidad de commits; úsela solo para una prueba puntual.

## §2 · Variables de entorno (Service → Variables)
Copie el bloque y pegue los valores. Las cinco primeras son las mismas credenciales de Colab — el par RSA se reutiliza tal cual:

```
SF_ACCOUNT              = <su cuenta>
SF_USER                 = SVC_EXPORTBOT
SF_ROLE                 = R_EXPORTBOT_APP
SF_WAREHOUSE            = APPS_WH
SF_PRIVATE_KEY_B64_1    = <Base64 del PEM privado — §0.2 de la guía 04>
SF_PRIVATE_KEY_B64_2    = <vacío hoy; se llena al rotar llaves>

SF_SEMANTIC_VIEW        = DWH_PROCOLOMBIA_SNOWFLAKE.SILVER.SV_EXPORTACIONES
SF_ESQUEMA_TELEMETRIA   = DB_EXPORTBOT.TELEMETRY
SF_CORTEX_MODELO        = claude-sonnet-4-6
PROVEEDOR_REDACCION     = cortex
TELEMETRIA_ACTIVA       = true

ENTORNO_APP             = railway
ARRANQUE_ESTRICTO       = true
ADMIN_TOKEN             = <token largo aleatorio — ej. salida de: openssl rand -hex 32>
```

Notas de criterio: `ARRANQUE_ESTRICTO=true` es la diferencia deliberada con Colab — en producción, una configuración incompleta debe **tumbar** el arranque, no degradarlo en silencio. `ADMIN_TOKEN` vacío deja `/metricas` cerrado (401): póngalo solo si va a usar el panel. No defina `CORS_ORIGENES`: el backend sirve el SPA desde el mismo dominio y abrir orígenes extra sin necesidad es superficie gratis.

## §3 · Verificación post-deploy (5 min, en orden)

1. **Salud:** `https://<su-app>.up.railway.app/api/salud` → `"estado": "ok"`, `"auth_snowflake": "keypair"`, `"entorno": "railway"`, `"telemetria": true`, `problemas_configuracion: []`.
2. **Funcional:** una pregunta real en la UI pública; confirme etapas SSE y cifras.
3. **Telemetría:** en Snowsight, los mismos SELECT de la §5 de la guía 04 — ahora deben aparecer filas con `ENVIRONMENT='railway'`. Ver ambos entornos separados en la misma tabla es la prueba de que la columna paga su existencia.
4. **Panel (si activó ADMIN_TOKEN):** `GET /api/metricas/resumen` con cabecera `X-Admin-Token` → KPIs; sin cabecera → 401.
5. **Mínimo privilegio en producción:** nada que hacer — es el mismo rol de solo lectura ya probado; la app no puede borrar ni modificar aunque la comprometan.

## §4 · Checklist go-live (el orden importa)
1. Eval ≥ 90 % en Colab (guía 04 §6) — **bloqueante**.
2. Conteo de verified queries confirmado (04 §0.3) — la vista desplegada es la que usted cree.
3. Deploy desde GitHub con las variables de §2 y `ARRANQUE_ESTRICTO=true`.
4. §3 completa en verde.
5. Anuncio interno con la URL y dos preguntas de ejemplo; primeros usuarios = su equipo (el feedback 👍/👎 ya queda en `FEEDBACK` con `ENVIRONMENT='railway'`).
6. A los 7 días: revisar `V_CALIDAD_RESPUESTAS` y `V_USO_DIARIO`; decidir con datos si Opus 4.7 merece el sobrecosto como opción del selector.

## §5 · Operación y costos (guardas mínimas)
- **Railway:** el servicio duerme/escala según plan; `railway.toml` ya fija healthcheck a `/api/salud`. Logs: Service → Deployments → View logs (busque `Telemetría activa hacia DB_EXPORTBOT.TELEMETRY` al arranque).
- **Snowflake:** el costo variable vive en el warehouse (`APPS_WH`, auto-suspend ya configurado) y en Cortex. Vigilancia mensual:

```sql
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY
ORDER BY START_TIME DESC LIMIT 20;
```

- **Rotación de llaves (cada 6–12 meses):** genere el par 2 → `ALTER USER ... SET RSA_PUBLIC_KEY_2` → cargue `SF_PRIVATE_KEY_B64_2` en Railway → redeploy → cuando todo use la 2, limpie la 1. El failover del backend hace que el orden no cause downtime.
- **Incidentes:** `docs/RUNBOOK.md` del repo (síntoma → causa probable → acción), escrito para que cualquiera del equipo lo siga sin contexto.

## §6 · Qué pegarme de vuelta
- JSON completo de `/api/salud` en Railway.
- Una fila de `EVENT_LOG` y una de `CHAT_LOG` con `ENVIRONMENT='railway'`.
- Con eso declaro la fase de despliegue cerrada y el pendiente restante queda en un solo lugar: la calidad medida por eval + feedback, que es donde debe vivir.
