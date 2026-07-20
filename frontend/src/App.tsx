/** Enrutamiento de ExportBot: chat público y /metricas oculta (sin enlace) + protegida. */

import { BrowserRouter, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import MetricasPage from "./pages/MetricasPage";

function Barra() {
  return (
    <header className="barra">
      <img src="/LogoProColombia.png" alt="ProColombia" />
      <img src="/LogoMinCIT.png" alt="MinCIT" />
      <div>
        <h1>ExportBot 2.0</h1>
        <div className="sub">Cifras de exportaciones de bienes · Snowflake Cortex Analyst</div>
      </div>
      <div className="relleno" />
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Barra />
      <Routes>
        <Route path="/" element={<ChatPage />} />
        {/* Ruta sin enlace en la barra; además exige ADMIN_TOKEN en la API (D9). */}
        <Route path="/metricas" element={<MetricasPage />} />
      </Routes>
      <footer className="pie">
        La información generada por IA puede contener errores; verifíquela con la SQL y los datos de origen.
        Uso interno · GIC · ProColombia.
      </footer>
    </BrowserRouter>
  );
}
