/** Panel interno /metricas — protegido por token (D9), consume las vistas V_*. */

import { useEffect, useMemo, useState } from "react";
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import { metricas } from "../api/cliente";

const Plot = createPlotlyComponent(Plotly);

interface Resumen {
  kpis: {
    CONSULTAS?: number;
    EXITOSAS?: number;
    LATENCIA_PROM_MS?: number;
    LATENCIA_P95_MS?: number;
    SESIONES?: number;
  };
  feedback: { POSITIVOS?: number; NEGATIVOS?: number };
}
interface Series {
  dias: { DIA: string; CONSULTAS: number; EXITOSAS: number; LATENCIA_PROM_MS?: number }[];
}
interface Preguntas {
  top: { PREGUNTA_NORM: string; VECES: number; EXITOSAS: number }[];
}
interface Feedback {
  feedback: { TS: string; UTIL: boolean; COMENTARIO: string; PREGUNTA: string }[];
}

const CLAVE_TOKEN = "exportbot_admin_token";

export default function MetricasPage() {
  const [token, setToken] = useState(sessionStorage.getItem(CLAVE_TOKEN) ?? "");
  const [borrador, setBorrador] = useState("");
  const [error, setError] = useState("");
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [series, setSeries] = useState<Series | null>(null);
  const [preguntas, setPreguntas] = useState<Preguntas | null>(null);
  const [fb, setFb] = useState<Feedback | null>(null);

  useEffect(() => {
    if (!token) return;
    setError("");
    Promise.all([
      metricas<Resumen>("resumen", token),
      metricas<Series>("series", token),
      metricas<Preguntas>("preguntas", token),
      metricas<Feedback>("feedback", token),
    ])
      .then(([r, s, p, f]) => {
        setResumen(r);
        setSeries(s);
        setPreguntas(p);
        setFb(f);
        sessionStorage.setItem(CLAVE_TOKEN, token);
      })
      .catch((e: Error) => {
        setError(e.message);
        if (e.message.includes("Token")) {
          sessionStorage.removeItem(CLAVE_TOKEN);
          setToken("");
        }
      });
  }, [token]);

  const grafico = useMemo(() => {
    if (!series?.dias?.length) return null;
    const dias = [...series.dias].reverse();
    return {
      data: [
        { type: "bar", name: "Consultas", x: dias.map((d) => d.DIA), y: dias.map((d) => d.CONSULTAS), marker: { color: "#0b2e6b" } },
        { type: "bar", name: "Exitosas", x: dias.map((d) => d.DIA), y: dias.map((d) => d.EXITOSAS), marker: { color: "#f5b301" } },
      ],
      layout: {
        barmode: "group",
        margin: { t: 10, r: 10, b: 60, l: 40 },
        height: 300,
        legend: { orientation: "h" },
      },
    };
  }, [series]);

  if (!token) {
    return (
      <div className="acceso">
        <h2>Panel de métricas de ExportBot</h2>
        <p>Ingrese el token de administración (variable ADMIN_TOKEN del despliegue).</p>
        <input
          type="password"
          value={borrador}
          onChange={(e) => setBorrador(e.target.value)}
          placeholder="Token de administración"
        />
        <button onClick={() => setToken(borrador.trim())} disabled={!borrador.trim()}>
          Entrar
        </button>
        {error && <p className="aviso-error">{error}</p>}
      </div>
    );
  }

  const k = resumen?.kpis ?? {};
  const tasa = k.CONSULTAS ? Math.round(((k.EXITOSAS ?? 0) / k.CONSULTAS) * 100) : 0;

  return (
    <div className="metricas">
      <h2>Métricas de uso · últimos 30 días</h2>
      {error && <p className="aviso-error">{error}</p>}
      <div className="kpis">
        <div className="kpi"><div className="valor">{k.CONSULTAS ?? "—"}</div><div className="nombre">Consultas</div></div>
        <div className="kpi"><div className="valor">{tasa}%</div><div className="nombre">Tasa de éxito</div></div>
        <div className="kpi"><div className="valor">{k.LATENCIA_PROM_MS ?? "—"}</div><div className="nombre">Latencia prom. (ms)</div></div>
        <div className="kpi"><div className="valor">{k.LATENCIA_P95_MS ?? "—"}</div><div className="nombre">Latencia p95 (ms)</div></div>
        <div className="kpi"><div className="valor">{k.SESIONES ?? "—"}</div><div className="nombre">Sesiones</div></div>
        <div className="kpi">
          <div className="valor">👍 {resumen?.feedback.POSITIVOS ?? 0} · 👎 {resumen?.feedback.NEGATIVOS ?? 0}</div>
          <div className="nombre">Feedback</div>
        </div>
      </div>

      {grafico && (
        <div className="panel">
          <h3>Consultas por día</h3>
          <Plot data={grafico.data as unknown[]} layout={grafico.layout} useResizeHandler style={{ width: "100%" }} />
        </div>
      )}

      <div className="panel">
        <h3>Preguntas más frecuentes</h3>
        <div className="tabla-envoltura">
          <table className="datos">
            <thead><tr><th>Pregunta (normalizada)</th><th>Veces</th><th>Exitosas</th></tr></thead>
            <tbody>
              {(preguntas?.top ?? []).map((p, i) => (
                <tr key={i}><td>{p.PREGUNTA_NORM}</td><td className="num">{p.VECES}</td><td className="num">{p.EXITOSAS}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel">
        <h3>Feedback reciente</h3>
        <div className="tabla-envoltura">
          <table className="datos">
            <thead><tr><th>Fecha</th><th>Útil</th><th>Pregunta</th><th>Comentario</th></tr></thead>
            <tbody>
              {(fb?.feedback ?? []).map((f, i) => (
                <tr key={i}>
                  <td>{String(f.TS).slice(0, 16)}</td>
                  <td>{f.UTIL ? "👍" : "👎"}</td>
                  <td>{f.PREGUNTA}</td>
                  <td>{f.COMENTARIO}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
