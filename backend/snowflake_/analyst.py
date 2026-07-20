"""Cliente REST de Snowflake Cortex Analyst (texto → SQL).

Envía la pregunta junto con la fuente semántica (vista semántica o YAML
en stage) al endpoint ``/api/v2/cortex/analyst/message`` y devuelve la
SQL generada. Autenticación: PAT (Bearer) o JWT firmado con la llave
privada RSA — el mismo par de llaves de la conexión del driver.

Referencia: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from config import Config

logger = logging.getLogger(__name__)

_VIGENCIA_JWT_S = 55 * 60  # < 1 h que exige Snowflake; se renueva antes


class ErrorAnalyst(RuntimeError):
    """Fallo del servicio Cortex Analyst (auth, cuota o respuesta inválida)."""


# ── JWT para llaves RSA (lógica del generador oficial de Snowflake) ─────


def _cuenta_para_jwt(cuenta_cruda: str) -> str:
    """Normaliza el identificador de cuenta al formato que exige el JWT."""
    cuenta = cuenta_cruda
    if ".global" not in cuenta.lower():
        idx = cuenta.find(".")
        if idx > 0:
            cuenta = cuenta[:idx]
    else:
        idx = cuenta.find("-")
        if idx > 0:
            cuenta = cuenta[:idx]
    return cuenta.upper()


class GeneradorJWT:
    """Genera y cachea el token JWT de llave pública/privada para las APIs REST."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._token: str = ""
        self._expira: float = 0.0

    def _firmar(self) -> str:
        import jwt as pyjwt
        from cryptography.hazmat.primitives import serialization

        cfg = self._cfg
        b64 = cfg.sf_private_key_b64_1 or cfg.sf_private_key_b64_2
        frase = cfg.sf_key_passphrase_1 if cfg.sf_private_key_b64_1 else cfg.sf_key_passphrase_2
        if not b64:
            raise ErrorAnalyst("No hay llave privada para firmar el JWT (SF_PRIVATE_KEY_B64_*).")
        pem = base64.b64decode(b64)
        llave = serialization.load_pem_private_key(pem, password=frase.encode() or None)
        publica_der = llave.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        huella = "SHA256:" + base64.b64encode(hashlib.sha256(publica_der).digest()).decode()
        calificado = f"{_cuenta_para_jwt(cfg.sf_account)}.{cfg.sf_user.upper()}"
        ahora = int(time.time())
        payload = {
            "iss": f"{calificado}.{huella}",
            "sub": calificado,
            "iat": ahora,
            "exp": ahora + _VIGENCIA_JWT_S,
        }
        return pyjwt.encode(payload, llave, algorithm="RS256")

    def token(self) -> str:
        """Devuelve un JWT vigente, renovándolo con 5 minutos de margen."""
        if not self._token or time.time() > self._expira - 300:
            self._token = self._firmar()
            self._expira = time.time() + _VIGENCIA_JWT_S
        return self._token


# ── Cliente del servicio ────────────────────────────────────────────────


@dataclass
class RespuestaAnalyst:
    """SQL y texto devueltos por Cortex Analyst para una pregunta."""

    sql: str = ""
    interpretacion: str = ""
    sugerencias: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    request_id: str = ""
    contenido_crudo: list[dict[str, Any]] = field(default_factory=list)


def parsear_respuesta(cuerpo: dict[str, Any]) -> RespuestaAnalyst:
    """Extrae SQL/texto/sugerencias del cuerpo JSON del servicio (defensivo)."""
    r = RespuestaAnalyst(request_id=str(cuerpo.get("request_id", "")))
    mensaje = cuerpo.get("message") or {}
    contenido = mensaje.get("content") or []
    if isinstance(contenido, list):
        r.contenido_crudo = [c for c in contenido if isinstance(c, dict)]
        for bloque in r.contenido_crudo:
            tipo = bloque.get("type")
            if tipo == "sql" and not r.sql:
                r.sql = str(bloque.get("statement", "")).strip()
            elif tipo == "text":
                r.interpretacion = (r.interpretacion + "\n" + str(bloque.get("text", ""))).strip()
            elif tipo == "suggestions":
                for s in bloque.get("suggestions") or []:
                    r.sugerencias.append(str(s))
    for adv in cuerpo.get("warnings") or []:
        r.advertencias.append(str(adv.get("message", adv)) if isinstance(adv, dict) else str(adv))
    return r


class ClienteAnalyst:
    """Llama a Cortex Analyst con la fuente semántica configurada."""

    RUTA = "/api/v2/cortex/analyst/message"

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._jwt = GeneradorJWT(cfg) if cfg.modo_auth == "keypair" else None

    def _cabeceras(self) -> dict[str, str]:
        cfg = self._cfg
        if cfg.modo_auth == "pat":
            return {
                "Authorization": f"Bearer {cfg.sf_pat}",
                "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        if self._jwt is not None:
            return {
                "Authorization": f"Bearer {self._jwt.token()}",
                "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        raise ErrorAnalyst("Sin credenciales para la API de Cortex Analyst.")

    def preguntar(self, pregunta: str, historial: list[dict[str, Any]] | None = None) -> RespuestaAnalyst:
        """Envía la pregunta (con historial opcional) y devuelve la respuesta parseada.

        Args:
            pregunta: Pregunta del usuario en lenguaje natural.
            historial: Turnos previos ya en el formato del servicio
                (``[{"role": "user"|"analyst", "content": [...]}, ...]``).

        Raises:
            ErrorAnalyst: ante HTTP ≠ 200 o cuerpo no interpretable.
        """
        cfg = self._cfg
        mensajes = list(historial or [])
        mensajes.append({"role": "user", "content": [{"type": "text", "text": pregunta}]})
        cuerpo: dict[str, Any] = {"messages": mensajes, **cfg.fuente_semantica}
        url = f"https://{cfg.host_rest}{self.RUTA}"
        try:
            resp = requests.post(url, json=cuerpo, headers=self._cabeceras(), timeout=cfg.timeout_analyst_s)
        except requests.RequestException as exc:  # red / DNS / timeout
            raise ErrorAnalyst(f"No se pudo contactar a Cortex Analyst: {exc}") from exc
        if resp.status_code != 200:
            raise ErrorAnalyst(f"Cortex Analyst HTTP {resp.status_code}: {resp.text[:400]}")
        try:
            return parsear_respuesta(resp.json())
        except ValueError as exc:
            raise ErrorAnalyst(f"Respuesta de Analyst no es JSON válido: {exc}") from exc
