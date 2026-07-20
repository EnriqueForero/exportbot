"""Pruebas E2E y visuales del frontend compilado de ExportBot.

Playwright carga los artefactos reales de ``frontend/dist`` dentro de una página
controlada e intercepta las APIs. No requiere Snowflake ni un servidor externo.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from playwright.sync_api import Page, Route, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"
CONTRACT = json.loads((ROOT / "contracts" / "exportbot_v2_contract.json").read_text(encoding="utf-8"))
pytestmark = pytest.mark.e2e


def _launch_browser(playwright):
    explicit = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    system = explicit or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    kwargs = {"headless": True}
    if system:
        kwargs["executable_path"] = system
    return playwright.chromium.launch(**kwargs)


def _dist_entrypoints() -> tuple[str, str]:
    html = (DIST / "index.html").read_text(encoding="utf-8")
    script = re.search(r'<script[^>]+src="([^"]+\.js)"', html)
    style = re.search(r'<link[^>]+href="([^"]+\.css)"', html)
    assert script and style, "frontend/dist/index.html no referencia JS/CSS de producción"
    return script.group(1), style.group(1)


def _mock_api_and_assets(page: Page) -> dict[str, int]:
    calls = {"chat": 0, "excel": 0, "pptx": 0, "feedback": 0}

    def handler(route: Route) -> None:
        url = route.request.url
        path = url.split("exportbot.test", 1)[-1].split("?", 1)[0]
        if path.startswith("/assets/"):
            asset = DIST / path.lstrip("/")
            if asset.exists():
                content_types = {".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}
                route.fulfill(
                    status=200,
                    content_type=content_types.get(asset.suffix, "application/octet-stream"),
                    headers={"Access-Control-Allow-Origin": "*"},
                    path=asset,
                )
            else:
                route.fulfill(status=404, body="asset missing")
            return
        if path in {"/LogoMinCIT.png", "/LogoProColombia.png"}:
            route.fulfill(status=200, content_type="image/png", path=DIST / path.lstrip("/"))
            return
        if path == "/api/proveedores":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "proveedores": [
                            {"id": "cortex", "nombre": "Cortex", "modelo": "snowflake-arctic", "disponible": "si"},
                            {"id": "openai", "nombre": "OpenAI", "modelo": "gpt-test", "disponible": "si"},
                        ]
                    }
                ),
            )
            return
        if path == "/api/chat":
            calls["chat"] += 1
            if calls["chat"] == 1:
                events = [
                    {"tipo": "etapa", "chat_id": "chat-1", "etapa": "analyst", "detalle": "Interpretando la pregunta…"},
                    {
                        "tipo": "final",
                        "chat_id": "chat-1",
                        "texto": "Colombia exportó 10.500 millones de USD FOB en el periodo consultado.",
                        "sql": "SELECT PAIS, SUM(VALOR) FROM EXPORTACIONES GROUP BY 1 LIMIT 5000",
                        "columnas": ["PAIS", "TOTAL_USD_FOB"],
                        "filas": [["Estados Unidos", 7500], ["China", 3000]],
                        "n_filas": 2,
                        "truncado": False,
                        "sugerencias": ["¿Cuáles fueron los principales productos?"],
                        "meta": {
                            "proveedor": "Cortex",
                            "modelo": "snowflake-arctic",
                            "degradado": False,
                            "cifras_verificadas": True,
                            "latencia_analyst_ms": 120,
                            "latencia_sql_ms": 80,
                            "version_app": "2.0.0b2",
                            "fuente_semantica": "FACT_EXPORTACIONES_SL",
                            "intentos": 2,
                        },
                    },
                ]
            else:
                events = [{"tipo": "error", "chat_id": "chat-2", "mensaje": "Consulta simulada no disponible."}]
            body = "".join(f"data: {json.dumps(event, ensure_ascii=False)}\n\n" for event in events)
            route.fulfill(status=200, content_type="text/event-stream", body=body)
            return
        if path == "/api/exportar/excel":
            calls["excel"] += 1
            route.fulfill(
                status=200,
                headers={
                    "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "Content-Disposition": 'attachment; filename="resultado.xlsx"',
                },
                body=b"PK-test-excel",
            )
            return
        if path == "/api/exportar/pptx":
            calls["pptx"] += 1
            route.fulfill(
                status=200,
                headers={
                    "Content-Type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "Content-Disposition": 'attachment; filename="resultado.pptx"',
                },
                body=b"PK-test-pptx",
            )
            return
        if path == "/api/track/feedback":
            calls["feedback"] += 1
            route.fulfill(status=200, content_type="application/json", body='{"ok": true}')
            return
        if path.startswith("/api/metricas/"):
            endpoint = path.rsplit("/", 1)[-1]
            payloads = {
                "resumen": {
                    "kpis": {
                        "CONSULTAS": 20,
                        "EXITOSAS": 18,
                        "LATENCIA_PROM_MS": 320,
                        "LATENCIA_P95_MS": 600,
                        "SESIONES": 7,
                    },
                    "feedback": {"POSITIVOS": 8, "NEGATIVOS": 1},
                },
                "series": {"dias": [{"DIA": "2026-07-19", "CONSULTAS": 4, "EXITOSAS": 4}]},
                "preguntas": {"top": [{"PREGUNTA_NORM": "TOP PAISES", "VECES": 5, "EXITOSAS": 5}]},
                "feedback": {
                    "feedback": [
                        {"TS": "2026-07-19T12:00:00", "UTIL": True, "COMENTARIO": "Útil", "PREGUNTA": "Top países"}
                    ]
                },
            }
            route.fulfill(status=200, content_type="application/json", body=json.dumps(payloads[endpoint]))
            return
        route.fulfill(status=404, body="not mocked")

    page.route("http://exportbot.test/**", handler)
    page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
    page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
    return calls


def _mount_app(page: Page, location: str = "/") -> None:
    script, style = _dist_entrypoints()
    page.set_content(
        f"""
        <!doctype html><html lang="es"><head>
          <base href="http://exportbot.test/">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <link rel="stylesheet" href="{style}">
        </head><body><div id="root"></div>
          <script>
            const __store = new Map();
            Object.defineProperty(window, "sessionStorage", {{
              value: {{
                getItem: (key) => __store.has(key) ? __store.get(key) : null,
                setItem: (key, value) => __store.set(key, String(value)),
                removeItem: (key) => __store.delete(key),
                clear: () => __store.clear(),
              }},
              configurable: true,
            }});
            const __listeners = new Map();
            const __location = {{
              pathname: {json.dumps(location)}, search: "", hash: "",
              origin: "http://exportbot.test",
              href: "http://exportbot.test" + {json.dumps(location)},
            }};
            const __history = {{
              state: {{idx: 0}},
              pushState(state, _unused, url) {{
                this.state = state;
                if (url) __location.pathname = new URL(String(url), __location.origin).pathname;
              }},
              replaceState(state, _unused, url) {{
                this.state = state;
                if (url) __location.pathname = new URL(String(url), __location.origin).pathname;
              }},
              go() {{}},
            }};
            window.__EXPORTBOT_TEST_BASENAME__ = "/";
            window.__EXPORTBOT_TEST_LOCATION__ = {json.dumps(location)};
            window.__EXPORTBOT_ROUTER_WINDOW__ = {{
              history: __history,
              location: __location,
              document: window.document,
              addEventListener: (name, fn) => __listeners.set(name, fn),
              removeEventListener: (name) => __listeners.delete(name),
            }};
          </script>
        </body></html>
        """,
        wait_until="load",
    )
    bundle = (DIST / script.lstrip("/")).read_text(encoding="utf-8")
    bundle = re.sub(r"export\{[^}]+\};?\s*$", "", bundle)
    page.evaluate("(code) => new Function(code)()", bundle)


def _assert_visual_matches(current_path: Path, baseline_name: str) -> None:
    settings = CONTRACT["visual_baseline"]
    baseline = ROOT / settings["files"][baseline_name]
    if os.environ.get("UPDATE_VISUAL_BASELINE") == "1":
        baseline.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(current_path, baseline)
        return
    assert baseline.exists(), "Falta línea base visual; use UPDATE_VISUAL_BASELINE=1 solo tras aprobar la interfaz."
    expected = Image.open(baseline).convert("RGB")
    current = Image.open(current_path).convert("RGB")
    assert current.size == expected.size, f"Dimensiones cambiaron: {current.size} != {expected.size}"

    # Normaliza diferencias menores de antialiasing/fuentes entre Chromium local y CI.
    scale = float(settings.get("comparison_scale", 1.0))
    compare_size = (max(1, round(current.width * scale)), max(1, round(current.height * scale)))
    expected = expected.resize(compare_size, Image.Resampling.LANCZOS)
    current = current.resize(compare_size, Image.Resampling.LANCZOS)
    blur = float(settings.get("blur_radius", 0.0))
    if blur:
        expected = expected.filter(ImageFilter.GaussianBlur(blur))
        current = current.filter(ImageFilter.GaussianBlur(blur))

    difference = ImageChops.difference(expected, current).convert("L")
    threshold = int(settings["pixel_threshold"])
    mask = difference.point(lambda pixel: 255 if pixel > threshold else 0)
    ratio = mask.histogram()[255] / (current.width * current.height)
    assert ratio <= float(settings["max_changed_pixel_ratio"]), (
        f"Regresión visual: {ratio:.2%} de píxeles cambiaron; máximo permitido "
        f"{settings['max_changed_pixel_ratio']:.2%}. Revise la captura antes de actualizar la línea base."
    )


def test_frontend_contract_and_visual_regression(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright)
        context = browser.new_context(viewport={"width": 1440, "height": 1100}, locale="es-CO", accept_downloads=True)
        page = context.new_page()
        calls = _mock_api_and_assets(page)
        page.emulate_media(reduced_motion="reduce")
        _mount_app(page)

        page.get_by_role("heading", name="Converse con las cifras de exportaciones de Colombia").wait_for()
        page.get_by_label("Proveedor de redacción").select_option("openai")

        screenshot = tmp_path / "exportbot_inicio_actual.png"
        page.screenshot(path=str(screenshot), full_page=True, animations="disabled", caret="hide")
        _assert_visual_matches(screenshot, "inicio")

        question = "¿Cuánto exportó Colombia en 2025?"
        query = page.get_by_placeholder(
            "Ej.: ¿Cuánto exportó Antioquia a Estados Unidos en 2025 y cuáles fueron los principales productos?"
        )
        query.fill(question)
        query.press("Enter")

        page.get_by_text("Colombia exportó 10.500 millones de USD FOB").wait_for()
        assert page.get_by_text("SQL autocorregida (2 intentos)").is_visible()
        assert page.get_by_role("cell", name="Estados Unidos").is_visible()
        assert page.get_by_text("Cifras verificadas").is_visible()
        page.get_by_text("Ver la SQL ejecutada").click()
        assert page.get_by_text("SELECT PAIS").is_visible()
        assert page.get_by_text("¿Cuáles fueron los principales productos?").is_visible()

        result_screenshot = tmp_path / "exportbot_resultado_actual.png"
        page.screenshot(path=str(result_screenshot), full_page=True, animations="disabled", caret="hide")
        _assert_visual_matches(result_screenshot, "resultado")

        with page.expect_download() as excel_download:
            page.get_by_role("button", name="Descargar Excel").click()
        assert excel_download.value.suggested_filename == "exportbot.xlsx"
        with page.expect_download() as pptx_download:
            page.get_by_role("button", name="Descargar presentación").click()
        assert pptx_download.value.suggested_filename == "exportbot.pptx"

        page.get_by_role("button", name="Marcar respuesta como útil").click()
        assert page.get_by_role("button", name="Marcar respuesta como útil").is_disabled()
        assert calls["feedback"] == 1

        query.fill("Provocar error de prueba")
        query.press("Enter")
        page.get_by_text("Consulta simulada no disponible.").wait_for()

        # El panel lazy se valida por compilación y contrato estático. Ejecutarlo desde
        # about:blank obligaría a alterar la semántica de importación de Vite.
        metrics_source = (ROOT / "frontend" / "src" / "pages" / "MetricasPage.tsx").read_text(encoding="utf-8")
        for protected_text in ("Token de administración", "Entrar al panel", "Métricas de uso", "Cerrar sesión"):
            assert protected_text in metrics_source

        assert calls == {"chat": 2, "excel": 1, "pptx": 1, "feedback": 1}

        # Control negativo: el comparador debe bloquear un cambio visual amplio.
        altered = tmp_path / "exportbot_inicio_alterado.png"
        altered_image = Image.open(ROOT / CONTRACT["visual_baseline"]["files"]["inicio"]).convert("RGB")
        draw = ImageDraw.Draw(altered_image)
        draw.rectangle((0, 0, altered_image.width, altered_image.height // 3), fill=(255, 255, 255))
        altered_image.save(altered)
        with pytest.raises(AssertionError, match="Regresión visual"):
            _assert_visual_matches(altered, "inicio")

        context.close()
        browser.close()
