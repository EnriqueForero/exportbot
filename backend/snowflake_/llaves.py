"""Carga tolerante de la llave privada RSA (una sola fuente de verdad).

Acepta los tres formatos que la práctica produce en ``SF_PRIVATE_KEY_B64_*``:

1. **PEM completo codificado en Base64** (el formato documentado:
   ``base64 -w0 rsa_exportbot_1.p8``).
2. **DER codificado en Base64** — lo que resulta de copiar solo el cuerpo
   del PEM sin las cabeceras ``BEGIN/END`` (confusión frecuente porque
   Snowflake pide la llave PÚBLICA exactamente así).
3. **PEM crudo** pegado directamente (con cabeceras y saltos de línea).

El diagnóstico de arranque usa :func:`describir_llave` para declarar en
``/api/salud`` si la llave es legible y con qué huella, ANTES de la
primera consulta — un secreto ilegible debe gritar al arrancar, no
explotar en el primer uso.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from typing import Any

_CABECERA_PEM = b"-----BEGIN"


def cargar_llave_privada(valor: str, passphrase: str = "") -> Any:
    """Devuelve la llave privada a partir del valor del secreto, sea cual sea su formato.

    Args:
        valor: Contenido de ``SF_PRIVATE_KEY_B64_n`` (PEM-b64, DER-b64 o PEM crudo).
        passphrase: Frase de cifrado; cadena vacía si la llave no está cifrada.

    Raises:
        ValueError: con un mensaje en español que nombra el formato detectado
            y la corrección exacta, para que el error sea accionable.
    """
    from cryptography.hazmat.primitives import serialization

    texto = (valor or "").strip().strip('"').strip("'")
    clave = passphrase.encode() or None
    if not texto:
        raise ValueError("La variable de la llave privada está vacía.")

    # Formato 3: PEM crudo pegado tal cual (no era Base64).
    if texto.startswith("-----BEGIN"):
        return serialization.load_pem_private_key(texto.encode(), password=clave)

    try:
        crudo = base64.b64decode(texto, validate=True)
    except binascii.Error as exc:
        raise ValueError(
            "El valor no es Base64 válido ni un PEM: revise que copió el secreto "
            "completo, sin espacios ni comillas. Lo esperado: la salida de "
            "`base64 -w0 <llave>.p8` en una sola línea."
        ) from exc

    if crudo.startswith(_CABECERA_PEM):  # Formato 1: PEM-b64 (documentado)
        return serialization.load_pem_private_key(crudo, password=clave)

    if crudo[:1] == b"\x30":  # Formato 2: DER (ASN.1 SEQUENCE) — cuerpo sin cabeceras
        return serialization.load_der_private_key(crudo, password=clave)

    raise ValueError(
        "El Base64 decodifica, pero el contenido no es una llave PEM ni DER "
        f"(primeros bytes: {crudo[:8]!r}). Probablemente codificó el archivo "
        "equivocado; regenere el secreto con `base64 -w0` sobre el .p8 privado."
    )


def llave_a_der_pkcs8(llave: Any) -> bytes:
    """DER PKCS#8 sin cifrar — el formato que exige el conector de Snowflake."""
    from cryptography.hazmat.primitives import serialization

    return llave.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def huella_publica(llave: Any) -> str:
    """Huella ``SHA256:<b64>`` de la llave pública — comparable con ``DESC USER``."""
    from cryptography.hazmat.primitives import serialization

    der = llave.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return "SHA256:" + base64.b64encode(hashlib.sha256(der).digest()).decode()


def describir_llave(valor: str, passphrase: str = "") -> tuple[bool, str]:
    """(legible, detalle) para el diagnóstico de arranque y ``/api/salud``.

    Nunca lanza: un secreto roto se reporta como texto, no como excepción.
    """
    try:
        llave = cargar_llave_privada(valor, passphrase)
    except Exception as exc:  # noqa: BLE001 - el motivo viaja como dato
        return False, str(exc)[:300]
    return True, huella_publica(llave)
