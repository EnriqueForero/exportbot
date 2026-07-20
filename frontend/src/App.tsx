/** Enrutamiento y marco institucional de ExportBot. */

import { lazy, Suspense } from "react";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import logoColor from "./assets/logos/procolombia-color.svg";
import logoBlanco from "./assets/logos/mincit-procolombia-blanco.svg";
import ChatPage from "./pages/ChatPage";
const MetricasPage = lazy(() => import("./pages/MetricasPage"));

function Encabezado() {
  return (
    <header className="navbar">
      <div className="wrap navbar__interior">
        <Link to="/" className="navbar__marca" aria-label="Ir al inicio de ExportBot">
          <img className="navbar__logo" src={logoColor} alt="ProColombia" />
          <span className="navbar__titulos">
            <span className="nav-title">ExportBot</span>
            <span className="nav-sub">Coordinación de Analítica · Gerencia de Inteligencia Comercial</span>
          </span>
        </Link>
        <nav className="navbar__nav" aria-label="Secciones de ExportBot">
          <a className="nav-enlace" href="/#consultar">Consultar</a>
          <a className="nav-enlace" href="/#como-funciona">Cómo funciona</a>
        </nav>
      </div>
    </header>
  );
}

function PieLegal() {
  return (
    <footer className="pie-institucional">
      <div className="wrap pie-institucional__grid">
        <div>
          <img className="pie-institucional__logo" src={logoBlanco} alt="MinCIT y ProColombia" />
        </div>
        <div>
          <b>ExportBot</b><br />
          Coordinación de Analítica · Gerencia de Inteligencia Comercial. Consulta en lenguaje natural sobre
          cifras oficiales de exportaciones de bienes.
        </div>
        <div>
          <b>Trazabilidad y datos</b><br />
          Cada respuesta expone la SQL ejecutada, la fuente y el resultado utilizado. Verifique la información
          antes de usarla en decisiones o publicaciones.
        </div>
        <div className="pie-institucional__aviso">
          <b>AVISO INSTITUCIONAL.</b> La información generada por IA puede contener errores. Uso interno · Fuente
          principal: Snowflake Cortex Analyst · v2.0.0.
        </div>
      </div>
    </footer>
  );
}

export default function App() {
  const testWindow = window as Window & {
    __EXPORTBOT_TEST_BASENAME__?: string;
    __EXPORTBOT_TEST_LOCATION__?: string;
    __EXPORTBOT_ROUTER_WINDOW__?: Window;
  };
  return (
    <BrowserRouter
      basename={testWindow.__EXPORTBOT_TEST_BASENAME__}
      window={testWindow.__EXPORTBOT_ROUTER_WINDOW__}
    >
      <div className="shell">
        <Encabezado />
        <main className="main-content">
          <Routes location={testWindow.__EXPORTBOT_TEST_LOCATION__}>
            <Route path="/" element={<ChatPage />} />
            <Route path="/metricas" element={<Suspense fallback={<div className="cargando-pagina"><span className="spinner" /> Cargando métricas…</div>}><MetricasPage /></Suspense>} />
          </Routes>
        </main>
        <PieLegal />
      </div>
    </BrowserRouter>
  );
}
