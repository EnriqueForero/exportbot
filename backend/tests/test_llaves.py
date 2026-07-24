"""Cargador tolerante de llaves RSA: los tres formatos reales y el fail-fast.

El incidente 2026-07-23 (Secret con el cuerpo del PEM sin cabeceras = DER-b64)
motivó este módulo: un secreto válido debe serlo en todas las capas, y uno
roto debe explicarse en español al arrancar, no reventar en la primera consulta.
"""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from snowflake_.llaves import cargar_llave_privada, describir_llave, huella_publica, llave_a_der_pkcs8


@pytest.fixture(scope="module")
def par_llaves():
    llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = (
        llave.private_key_bytes
        if False
        else llave.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )
    der = llave.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    return llave, pem, der


def test_acepta_pem_base64_formato_documentado(par_llaves):
    llave, pem, _ = par_llaves
    cargada = cargar_llave_privada(base64.b64encode(pem).decode())
    assert huella_publica(cargada) == huella_publica(llave)


def test_acepta_der_base64_cuerpo_sin_cabeceras(par_llaves):
    """El formato del incidente: solo el cuerpo del PEM (== DER en Base64)."""
    llave, _, der = par_llaves
    cargada = cargar_llave_privada(base64.b64encode(der).decode())
    assert huella_publica(cargada) == huella_publica(llave)


def test_acepta_pem_crudo_pegado(par_llaves):
    llave, pem, _ = par_llaves
    cargada = cargar_llave_privada(pem.decode())
    assert huella_publica(cargada) == huella_publica(llave)


def test_llave_cifrada_exige_passphrase(par_llaves):
    llave, _, _ = par_llaves
    pem_cifrado = llave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"secreto"),
    )
    b64 = base64.b64encode(pem_cifrado).decode()
    with pytest.raises((TypeError, ValueError)):
        cargar_llave_privada(b64)  # sin frase debe fallar
    assert huella_publica(cargar_llave_privada(b64, "secreto")) == huella_publica(llave)


def test_basura_da_mensaje_accionable():
    with pytest.raises(ValueError) as exc:
        cargar_llave_privada("esto no es una llave ###")
    assert "Base64" in str(exc.value)


def test_describir_llave_no_lanza_y_da_veredicto(par_llaves):
    _, pem, _ = par_llaves
    ok, detalle = describir_llave(base64.b64encode(pem).decode())
    assert ok and detalle.startswith("SHA256:")
    ok2, detalle2 = describir_llave("no-valido")
    assert not ok2 and detalle2


def test_der_pkcs8_para_el_conector(par_llaves):
    llave, _, der = par_llaves
    assert llave_a_der_pkcs8(llave) == der
