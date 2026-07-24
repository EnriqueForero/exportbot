"""Harness de la suite dorada: compara el flujo real contra la SQL de referencia.

Requiere credenciales Snowflake en el entorno (mismas variables de la app).
Ejecución:  python eval/evaluar.py [--limite N] [--solo G03]
Escribe eval/resultados/eval_YYYYMMDD_HHMM.json y sale con código ≠ 0 si la
exactitud queda por debajo del umbral del contrato (DoD ≥ 90 %).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

from config import cargar_config
from motores.guardas import validar_sql
from snowflake_.analyst import ClienteAnalyst
from snowflake_.conexion import GestorConexion
from snowflake_.ejecutor import ejecutar_select


def _normalizar(filas: list[list]) -> list[tuple]:
    """Hace comparable un resultado: redondea números y ordena filas."""
    norm = []
    for fila in filas:
        norm.append(tuple(round(v, 2) if isinstance(v, float) else v for v in fila))
    return sorted(norm, key=lambda t: tuple(str(x) for x in t))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalúa ExportBot contra la suite dorada.")
    parser.add_argument("--limite", type=int, default=0, help="Evaluar solo las N primeras con SQL de referencia.")
    parser.add_argument("--solo", type=str, default="", help="Evaluar un id puntual (ej. G03).")
    args = parser.parse_args()

    suite = yaml.safe_load((RAIZ / "semantic" / "preguntas_doradas.yaml").read_text(encoding="utf-8"))
    umbral = float(suite.get("umbral_exactitud", 0.9))
    casos = [c for c in suite["preguntas"] if c.get("sql_referencia")]
    if args.solo:
        casos = [c for c in casos if c["id"] == args.solo]
    if args.limite:
        casos = casos[: args.limite]
    if not casos:
        print("No hay casos con sql_referencia para evaluar.")
        return 2

    cfg = cargar_config()
    problemas = cfg.validar()
    if problemas:
        print("Configuración incompleta:", " | ".join(problemas))
        return 2
    gestor = GestorConexion(cfg, query_tag="EXPORTBOT_EVAL")
    analyst = ClienteAnalyst(cfg)

    resultados, aciertos = [], 0
    for caso in casos:
        cid, pregunta = caso["id"], caso["pregunta"]
        registro = {"id": cid, "pregunta": pregunta, "ok": False, "motivo": ""}
        try:
            t0 = time.monotonic()
            resp = analyst.preguntar(pregunta)
            if not resp.sql:
                registro["motivo"] = "analyst_sin_sql"
                raise RuntimeError(registro["motivo"])
            v = validar_sql(resp.sql, cfg.esquemas_permitidos, cfg.max_filas_resultado)
            if not v.ok:
                registro["motivo"] = f"validacion: {v.motivo}"
                raise RuntimeError(registro["motivo"])
            conn = gestor.obtener()
            obtenido = ejecutar_select(conn, v.sql, cfg.max_filas_resultado)
            esperado = ejecutar_select(conn, caso["sql_referencia"], cfg.max_filas_resultado)
            iguales = _normalizar(obtenido.filas) == _normalizar(esperado.filas)
            registro.update(
                ok=iguales,
                motivo="" if iguales else "resultado_distinto",
                sql_generada=v.sql,
                n_filas=obtenido.n_filas,
                latencia_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as exc:  # noqa: BLE001 - el reporte captura el motivo
            registro["motivo"] = registro["motivo"] or str(exc)[:300]
        aciertos += int(bool(registro["ok"]))
        estado = "OK " if registro["ok"] else "FALLO"
        print(f"[{estado}] {cid} · {pregunta[:70]} · {registro['motivo'][:80]}")
        resultados.append(registro)

    exactitud = aciertos / len(casos)
    salida = RAIZ / "eval" / "resultados"
    salida.mkdir(parents=True, exist_ok=True)
    archivo = salida / f"eval_{time.strftime('%Y%m%d_%H%M')}.json"
    archivo.write_text(
        json.dumps({"exactitud": exactitud, "umbral": umbral, "casos": resultados}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nExactitud: {exactitud:.0%} (umbral {umbral:.0%}) → {archivo}")
    gestor.cerrar()
    return 0 if exactitud >= umbral else 1


if __name__ == "__main__":
    raise SystemExit(main())
