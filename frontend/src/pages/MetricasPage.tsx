/** Panel interno /metricas — protegido por token, con el mismo sistema visual institucional. */

import { useEffect, useMemo, useState } from "react";
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import Icon from "../components/Icon";
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
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  useEffect(() => {
    if (!token) return;
    setError("");
    Promise.all([
      metricas<Resumen>("resumen", token),
      metricas<Series>("series", token),
      metricas<Preguntas>("preguntas", token),
      metricas<Feedback>("feedback", token),
    ])
      .then(([respuestaResumen, respuestaSeries, respuestaPreguntas, respuestaFeedback]) => {
        setResumen(respuestaResumen);
        setSeries(respuestaSeries);
        setPreguntas(respuestaPreguntas);
        setFeedback(respuestaFeedback);
        sessionStorage.setItem(CLAVE_TOKEN, token);
      })
      .catch((fallo: Error) => {
        setError(fallo.message);
        if (fallo.message.includes("Token")) {
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
        {
          type: "bar",
          name: "Consultas",
          x: dias.map((dia) => dia.DIA),
          y: dias.map((dia) => dia.CONSULTAS),
          marker: { color: "#011627" },
        },
        {
          type: "bar",
          name: "Exitosas",
          x: dias.map((dia) => dia.DIA),
          y: dias.map((dia) => dia.EXITOSAS),
          marker: { color: "#ffa400" },
        },
      ],
      layout: {
        barmode: "group",
        margin: { t: 10, r: 10, b: 60, l: 40 },
        height: 310,
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        font: { family: "Jost, sans-serif", color: "#1c2530" },
        legend: { orientation: "h" },
        xaxis: { gridcolor: "#f0f1ef" },
        yaxis: { gridcolor: "#f0f1ef" },
      },
    };
  }, [series]);

  if (!token) {
    return (
      <div className="acceso">
        <section className="card">
          <div className="card__head">
            <div>
              <h2 className="card__titulo"><Icon name="chart" size={19} /> Panel de métricas</h2>
              <p className="card__sub">Acceso restringido para seguimiento operativo de ExportBot.</p>
              <span className="cinta" />
            </div>
          </div>
          <label className="selector-proveedor">
            <span>Token de administración</span>
            <input
              className="field"
              type="password"
              value={borrador}
              onChange={(evento) => setBorrador(evento.target.value)}
              onKeyDown={(evento) => {
                if (evento.key === "Enter" && borrador.trim()) setToken(borrador.trim());
              }}
              placeholder="Variable ADMIN_TOKEN del despliegue"
            />
          </label>
          <div className="acceso__acciones">
            <button className="btn btn-primary" onClick={() => setToken(borrador.trim())} disabled={!borrador.trim()}>
              Entrar al panel
            </button>
          </div>
          {error && <p className="aviso-error">{error}</p>}
        </section>
      </div>
    );
  }

  const kpis = resumen?.kpis ?? {};
  const tasa = kpis.CONSULTAS ? Math.round(((kpis.EXITOSAS ?? 0) / kpis.CONSULTAS) * 100) : 0;

  const cerrarSesion = () => {
    sessionStorage.removeItem(CLAVE_TOKEN);
    setToken("");
    setBorrador("");
    setResumen(null);
    setSeries(null);
    setPreguntas(null);
    setFeedback(null);
  };

  return (
    <div className="metricas">
      <div className="metricas__encabezado">
        <div>
          <h1>Métricas de uso</h1>
          <p>Comportamiento de ExportBot durante los últimos 30 días.</p>
          <span className="cinta" />
        </div>
        <button className="btn btn-ghost btn-sm" onClick={cerrarSesion}>Cerrar sesión</button>
      </div>

      {error && (
        <div className="aviso aviso--error" style={{ marginBottom: 16 }}>
          <Icon name="info" size={17} /> {error}
        </div>
      )}

      <section className="kpis" aria-label="Indicadores principales">
        <div className="kpi"><div className="valor">{kpis.CONSULTAS ?? "—"}</div><div className="nombre">Consultas</div></div>
        <div className="kpi"><div className="valor">{tasa}%</div><div className="nombre">Tasa de éxito</div></div>
        <div className="kpi"><div className="valor">{kpis.LATENCIA_PROM_MS ?? "—"}</div><div className="nombre">Latencia promedio (ms)</div></div>
        <div className="kpi"><div className="valor">{kpis.LATENCIA_P95_MS ?? "—"}</div><div className="nombre">Latencia p95 (ms)</div></div>
        <div className="kpi"><div className="valor">{kpis.SESIONES ?? "—"}</div><div className="nombre">Sesiones</div></div>
        <div className="kpi">
          <div className="valor">↑ {resumen?.feedback.POSITIVOS ?? 0} · ↓ {resumen?.feedback.NEGATIVOS ?? 0}</div>
          <div className="nombre">Feedback positivo · negativo</div>
        </div>
      </section>

      {grafico && (
        <section className="panel">
          <h3>Consultas por día</h3>
          <Plot data={grafico.data as unknown[]} layout={grafico.layout} useResizeHandler style={{ width: "100%" }} />
        </section>
      )}

      <section className="panel">
        <h3>Preguntas más frecuentes</h3>
        <div className="tbl-scroll">
          <table className="res">
            <thead><tr><th>Pregunta normalizada</th><th>Veces</th><th>Exitosas</th></tr></thead>
            <tbody>
              {(preguntas?.top ?? []).map((pregunta, indice) => (
                <tr key={indice}>
                  <td>{pregunta.PREGUNTA_NORM}</td>
                  <td className="tnum celda-num">{pregunta.VECES}</td>
                  <td className="tnum celda-num">{pregunta.EXITOSAS}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h3>Feedback reciente</h3>
        <div className="tbl-scroll">
          <table className="res">
            <thead><tr><th>Fecha</th><th>Útil</th><th>Pregunta</th><th>Comentario</th></tr></thead>
            <tbody>
              {(feedback?.feedback ?? []).map((item, indice) => (
                <tr key={indice}>
                  <td>{String(item.TS).slice(0, 16)}</td>
                  <td>{item.UTIL ? "Sí" : "No"}</td>
                  <td>{item.PREGUNTA}</td>
                  <td>{item.COMENTARIO}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
