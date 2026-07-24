"""Conexión a Snowflake con PAT o par de llaves RSA (rotación 1→2).

Porta a FastAPI el patrón probado en Tres Ejes / gestion_conocimiento:
llave privada en Base64 vía entorno (apto Railway/Colab), llave de
respaldo ante error JWT, reintentos solo en fallos transitorios y
``query_tag`` para trazabilidad. `snowflake-connector-python` se importa
de forma diferida para que el paquete cargue (y se pruebe) sin el driver.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from config import Config

logger = logging.getLogger(__name__)

_REINTENTOS = 3
_ESPERA_TRANSITORIA_S = 5
_MARCAS_ERROR_LLAVE = ("JWT token is invalid", "JWT_TOKEN_INVALID", "Private key")


def _cargar_llave_der(b64_pem: str, passphrase: str) -> bytes:
    """Convierte la llave privada (PEM-b64, DER-b64 o PEM crudo) al DER PKCS#8 del conector.

    La tolerancia de formato vive en :mod:`snowflake_.llaves` — misma lógica
    que usa el JWT de Cortex Analyst, para que un secreto válido lo sea en
    TODAS las capas o en ninguna.
    """
    from snowflake_.llaves import cargar_llave_privada, llave_a_der_pkcs8

    return llave_a_der_pkcs8(cargar_llave_privada(b64_pem, passphrase))


class GestorConexion:
    """Mantiene UNA conexión viva a Snowflake y la recrea cuando muere.

    Thread-safe: el orquestador, la telemetría y los routers piden la
    conexión vía :meth:`obtener`; los cursores son por llamada.
    """

    def __init__(self, cfg: Config, query_tag: str = "EXPORTBOT") -> None:
        self._cfg = cfg
        self._query_tag = query_tag
        self._conn: Any | None = None
        self._lock = threading.Lock()
        self._llave_preferida = 1  # recuerda cuál llave funcionó (rotación sin downtime)

    # ------------------------------------------------------------------
    def _kwargs_base(self) -> dict[str, Any]:
        cfg = self._cfg
        return {
            "account": cfg.sf_account,
            "user": cfg.sf_user,
            "role": cfg.sf_role or None,
            "warehouse": cfg.sf_warehouse or None,
            "database": cfg.sf_database or None,
            "schema": cfg.sf_schema or None,
            "client_session_keep_alive": True,
            "session_parameters": {
                "QUERY_TAG": self._query_tag,
                "STATEMENT_TIMEOUT_IN_SECONDS": cfg.timeout_sql_s,
                # Hora institucional en toda la sesión: los TIMESTAMP_LTZ de
                # telemetría se escriben/leen en Bogotá sin CONVERT_TIMEZONE.
                "TIMEZONE": cfg.zona_horaria,
            },
        }

    def _intentar(self, num_llave: int | None) -> Any:
        """Un intento de conexión con PAT (``num_llave=None``) o la llave dada."""
        import snowflake.connector  # import diferido (ver docstring del módulo)

        kwargs = self._kwargs_base()
        cfg = self._cfg
        if num_llave is None:
            kwargs["password"] = cfg.sf_pat  # el PAT reemplaza a la contraseña
        else:
            b64 = cfg.sf_private_key_b64_1 if num_llave == 1 else cfg.sf_private_key_b64_2
            frase = cfg.sf_key_passphrase_1 if num_llave == 1 else cfg.sf_key_passphrase_2
            if not b64:
                raise ValueError(f"SF_PRIVATE_KEY_B64_{num_llave} no está definida.")
            kwargs["private_key"] = _cargar_llave_der(b64, frase)
        return snowflake.connector.connect(**kwargs)

    def conectar(self) -> Any:
        """Crea la conexión con reintentos y failover de llave 1→2.

        Raises:
            RuntimeError: si todos los intentos fallan (mensaje con la causa).
        """
        cfg = self._cfg
        if cfg.modo_auth == "sin_credenciales":
            raise RuntimeError("Sin credenciales Snowflake (ni SF_PAT ni llaves RSA).")

        ordenes: list[int | None]
        if cfg.modo_auth == "pat":
            ordenes = [None]
        else:
            respaldo = 2 if self._llave_preferida == 1 else 1
            ordenes = [self._llave_preferida]
            if cfg.sf_private_key_b64_2 or cfg.sf_private_key_b64_1:
                ordenes.append(respaldo)

        ultimo_error: Exception | None = None
        for intento in range(_REINTENTOS):
            for num_llave in ordenes:
                try:
                    conn = self._intentar(num_llave)
                    if num_llave is not None:
                        self._llave_preferida = num_llave
                    logger.info("Conexión Snowflake establecida (auth=%s).", cfg.modo_auth)
                    return conn
                except Exception as exc:  # noqa: BLE001 - se clasifica abajo
                    ultimo_error = exc
                    texto = str(exc)
                    es_llave = any(marca in texto for marca in _MARCAS_ERROR_LLAVE)
                    logger.warning(
                        "Fallo de conexión (intento %s, llave=%s, error_llave=%s): %s",
                        intento + 1,
                        num_llave,
                        es_llave,
                        texto[:300],
                    )
                    if not es_llave:
                        break  # error transitorio: no rote llave, espere y reintente
            if intento < _REINTENTOS - 1:
                time.sleep(_ESPERA_TRANSITORIA_S)
        raise RuntimeError(f"Snowflake inaccesible tras {_REINTENTOS} intentos: {ultimo_error}")

    # ------------------------------------------------------------------
    def obtener(self) -> Any:
        """Devuelve la conexión viva; la (re)crea si no existe o está cerrada."""
        with self._lock:
            if self._conn is not None:
                try:
                    if not self._conn.is_closed():
                        return self._conn
                except Exception:
                    logger.debug("Conexión previa inutilizable; se recrea", exc_info=True)
            self._conn = self.conectar()
            return self._conn

    def fabrica(self) -> Callable[[], Any]:
        """Callable sin argumentos que entrega la conexión (para inyectar)."""
        return self.obtener

    def cerrar(self) -> None:
        """Cierra la conexión si existe (shutdown ordenado)."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    logger.debug("Cierre de conexión best-effort falló", exc_info=True)
                self._conn = None
