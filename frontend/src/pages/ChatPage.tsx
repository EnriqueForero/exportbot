/** Experiencia principal de ExportBot: portada institucional, consulta y resultados trazables. */

import { FormEvent, useEffect, useRef, useState } from "react";
import Icon from "../components/Icon";
import { chatStream, enviarFeedback, exportar, listarProveedores } from "../api/cliente";
import type { EventoFinal, Proveedor, Turno } from "../tipos";

const SUGERENCIAS = [
  "¿Cuánto exportó Colombia en USD FOB en 2025?",
  "Top 10 países destino por valor en 2025",
  "Exportaciones no mineras por departamento de origen en 2024",
  "¿Qué cadena productiva creció más entre 2023 y 2025?",
  "Top 5 empresas exportadoras de Antioquia en 2025",
  "Exportaciones a Estados Unidos por medio de transporte en 2025",
];

const PASOS = [
  {
    icono: "search" as const,
    titulo: "1 · Usted pregunta en español",
    detalle: "Formule la consulta con periodo, mercado, departamento, empresa o cadena productiva.",
  },
  {
    icono: "brain" as const,
    titulo: "2 · Analyst interpreta la intención",
    detalle: "El modelo semántico traduce conceptos de negocio a dimensiones, métricas y filtros válidos.",
  },
  {
    icono: "shield" as const,
    titulo: "3 · La consulta se valida",
    detalle: "El backend controla la SQL, limita el resultado y corrige una vez cuando la consulta falla.",
  },
  {
    icono: "database" as const,
    titulo: "4 · Snowflake devuelve evidencia",
    detalle: "La respuesta incluye cifras, tabla, SQL ejecutada, latencias y archivos exportables.",
  },
];

const NUM = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

function esNumero(valor: unknown): valor is number {
  return typeof valor === "number" && Number.isFinite(valor);
}

function Tabla({ final }: { final: EventoFinal }) {
  if (!final.columnas.length) return null;
  return (
    <>
      <div className="tbl-scroll">
        <table className="res">
          <thead>
            <tr>
              {final.columnas.map((columna) => <th key={columna}>{columna}</th>)}
            </tr>
          </thead>
          <tbody>
            {final.filas.map((fila, indiceFila) => (
              <tr key={indiceFila}>
                {fila.map((valor, indiceColumna) => (
                  <td key={indiceColumna} className={esNumero(valor) ? "tnum celda-num" : undefined}>
                    {valor === null ? "—" : esNumero(valor) ? NUM.format(valor) : String(valor)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {final.truncado && (
        <div className="nota-truncado">
          Mostrando {final.filas.length} de {final.n_filas} filas. La descarga incluye el resultado visible.
        </div>
      )}
    </>
  );
}

interface TarjetaProps {
  turno: Turno;
  onFeedback: (util: boolean) => void;
  onSugerencia: (pregunta: string) => void;
}

function TarjetaRespuesta({ turno, onFeedback, onSugerencia }: TarjetaProps) {
  const final = turno.final;
  const [exportando, setExportando] = useState<"" | "excel" | "pptx">("");
  if (!final) return null;

  const descargar = async (tipo: "excel" | "pptx") => {
    setExportando(tipo);
    try {
      await exportar(tipo, {
        pregunta: turno.pregunta,
        texto: final.texto,
        sql: final.sql,
        columnas: final.columnas,
        filas: final.filas,
        chat_id: final.chat_id,
      });
    } catch (error) {
      alert(error instanceof Error ? error.message : "No se pudo exportar el resultado.");
    } finally {
      setExportando("");
    }
  };

  return (
    <article className="card resultado-card">
      <header className="resultado-card__encabezado">
        <span className={`estado-punto ${final.meta.cifras_verificadas ? "estado-punto--ok" : "estado-punto--warn"}`} />
        <div className="resultado-card__titulos">
          <h2>{turno.pregunta}</h2>
          <div className="resultado-card__meta">
            {final.meta.proveedor}
            {final.meta.modelo ? ` · ${final.meta.modelo}` : ""}
            {final.meta.intentos > 1 ? " · SQL autocorregida" : ""}
          </div>
        </div>
      </header>

      <div className="respuesta-texto">{final.texto}</div>

      <div className="pills" aria-label="Metadatos de la respuesta">
        <span className="pill"><Icon name="database" size={12} /> Snowflake · {final.n_filas} fila(s)</span>
        <span className="pill">SQL {final.meta.latencia_sql_ms} ms</span>
        <span className="pill">Analyst {final.meta.latencia_analyst_ms} ms</span>
        <span className={`pill ${final.meta.cifras_verificadas ? "pill--ok" : "pill--warn"}`}>
          <Icon name={final.meta.cifras_verificadas ? "check" : "info"} size={12} />
          {final.meta.cifras_verificadas ? "Cifras verificadas" : "Redacción degradada"}
        </span>
      </div>

      {final.sql && (
        <details className="trace">
          <summary><Icon name="code" size={14} /> Ver la SQL ejecutada (trazabilidad)</summary>
          <pre className="sql">{final.sql}</pre>
        </details>
      )}

      <Tabla final={final} />

      <div className="resultado-card__acciones">
        <div className="resultado-card__descargas">
          {final.columnas.length > 0 && (
            <>
              <button className="btn btn-export btn-sm" disabled={exportando !== ""} onClick={() => void descargar("excel")}>
                <Icon name="download" size={14} />
                {exportando === "excel" ? "Generando…" : "Descargar Excel"}
              </button>
              <button className="btn btn-export btn-sm" disabled={exportando !== ""} onClick={() => void descargar("pptx")}>
                <Icon name="presentation" size={14} />
                {exportando === "pptx" ? "Generando…" : "Descargar presentación"}
              </button>
            </>
          )}
        </div>
        <div className="feedback" aria-label="Calificar respuesta">
          <span>¿Fue útil?</span>
          <button
            className={turno.feedback === true ? "feedback__boton feedback__boton--activo" : "feedback__boton"}
            disabled={turno.feedback !== undefined}
            onClick={() => onFeedback(true)}
            aria-label="Marcar respuesta como útil"
          >
            <Icon name="thumbUp" size={15} />
          </button>
          <button
            className={turno.feedback === false ? "feedback__boton feedback__boton--activo" : "feedback__boton"}
            disabled={turno.feedback !== undefined}
            onClick={() => onFeedback(false)}
            aria-label="Marcar respuesta como no útil"
          >
            <Icon name="thumbDown" size={15} />
          </button>
        </div>
      </div>

      {final.sugerencias.length > 0 && (
        <div className="siguientes-consultas">
          <div className="siguientes-consultas__titulo">
            <Icon name="bolt" size={14} /> Consultas relacionadas
          </div>
          <div className="lanzadores__chips">
            {final.sugerencias.slice(0, 4).map((sugerencia) => (
              <button className="chip" key={sugerencia} onClick={() => onSugerencia(sugerencia)}>
                <Icon name="search" size={12} /> {sugerencia}
              </button>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}

function Procesando({ turno }: { turno: Turno }) {
  const etapaActual = turno.etapas[turno.etapas.length - 1]?.detalle ?? "Preparando la consulta…";
  return (
    <div className="card procesando-card" role="status" aria-live="polite">
      <div className="procesando-card__fila">
        <span className="spinner procesando-card__spinner" aria-hidden="true" />
        <div>
          <div className="procesando-card__titulo">
            <Icon name="bolt" size={15} /> Procesando consulta
          </div>
          <div className="procesando-card__etapa">{etapaActual}</div>
        </div>
      </div>
      <div className="procesando-card__barra"><span /></div>
    </div>
  );
}

export default function ChatPage() {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [proveedor, setProveedor] = useState("cortex");
  const consultaRef = useRef<HTMLTextAreaElement>(null);
  const finalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listarProveedores().then(setProveedores).catch(() => setProveedores([]));
  }, []);

  useEffect(() => {
    finalRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turnos]);

  const enfocarConsulta = () => {
    document.getElementById("consultar")?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => consultaRef.current?.focus(), 450);
  };

  const preguntar = async (pregunta: string) => {
    const limpia = pregunta.trim();
    if (!limpia || ocupado) return;
    setOcupado(true);
    setTexto("");
    const id = Math.random().toString(36).slice(2);
    setTurnos((actuales) => [...actuales, { id, pregunta: limpia, etapas: [] }]);
    const actualizar = (fn: (turno: Turno) => Turno) =>
      setTurnos((lista) => lista.map((turno) => (turno.id === id ? fn(turno) : turno)));

    try {
      await chatStream(limpia, proveedor, (evento) => {
        if (evento.tipo === "etapa") actualizar((turno) => ({ ...turno, etapas: [...turno.etapas, evento] }));
        else if (evento.tipo === "final") actualizar((turno) => ({ ...turno, final: evento }));
        else actualizar((turno) => ({ ...turno, error: evento.mensaje }));
      });
    } catch {
      actualizar((turno) => ({ ...turno, error: "Se perdió la conexión con el servidor." }));
    } finally {
      setOcupado(false);
    }
  };

  const manejarEnvio = (evento: FormEvent) => {
    evento.preventDefault();
    void preguntar(texto);
  };

  const marcarFeedback = (id: string, util: boolean) => {
    const turno = turnos.find((item) => item.id === id);
    setTurnos((lista) => lista.map((item) => (item.id === id ? { ...item, feedback: util } : item)));
    if (turno?.final) void enviarFeedback(turno.final.chat_id, util);
  };

  return (
    <>
      <section className="hero-oceano">
        <div className="wrap">
          <div className="hero-oceano__eyebrow">Coordinación de Analítica · ProColombia</div>
          <h1 className="hero-oceano__titulo">
            Converse con las cifras de <span className="hero-oceano__acento">exportaciones de Colombia</span>
          </h1>
          <span className="cinta cinta--ancha" />
          <p className="hero-oceano__bajada">
            Pregunte en lenguaje natural sobre mercados, productos, departamentos, empresas y cadenas productivas.
            ExportBot traduce la intención mediante <strong>Snowflake Cortex Analyst</strong>, ejecuta la consulta y
            entrega una respuesta verificable con <strong>SQL, datos de origen y archivos exportables</strong>.
          </p>
          <div className="hero-oceano__cta">
            <button className="btn btn-accent btn-lg" onClick={enfocarConsulta}>
              <Icon name="search" size={17} /> Empezar a consultar
            </button>
            <a className="btn btn-invertido btn-lg" href="#como-funciona">
              <Icon name="info" size={16} /> Cómo funciona
            </a>
          </div>
        </div>
      </section>

      <div className="wrap contenido-principal">
        <section className="kpi-fila kpi-fila--flotante" aria-label="Cobertura de la fuente">
          <div className="kpi"><span className="kpi__valor">20+</span><span className="kpi__etiqueta">Años de serie histórica</span></div>
          <div className="kpi"><span className="kpi__valor">2026-04</span><span className="kpi__etiqueta">Último corte configurado</span></div>
          <div className="kpi"><span className="kpi__valor">Mensual</span><span className="kpi__etiqueta">Nivel de actualización</span></div>
          <div className="kpi"><span className="kpi__valor">SQL</span><span className="kpi__etiqueta">Trazabilidad visible</span></div>
        </section>

        <section id="consultar" className="card consulta-card">
          <div className="card__head">
            <div>
              <h2 className="card__titulo"><Icon name="search" size={18} /> Consulte la base de exportaciones</h2>
              <p className="card__sub">
                Sea específico con el periodo y la dimensión que necesita. Puede preguntar en español sin conocer SQL.
              </p>
              <span className="cinta" />
            </div>
          </div>

          <form onSubmit={manejarEnvio} className="consulta-form">
            <textarea
              ref={consultaRef}
              className="field consulta-form__texto"
              rows={3}
              value={texto}
              onChange={(evento) => setTexto(evento.target.value)}
              onKeyDown={(evento) => {
                if (evento.key === "Enter" && !evento.shiftKey) {
                  evento.preventDefault();
                  if (texto.trim() && !ocupado) void preguntar(texto);
                }
              }}
              placeholder="Ej.: ¿Cuánto exportó Antioquia a Estados Unidos en 2025 y cuáles fueron los principales productos?"
              maxLength={800}
              disabled={ocupado}
            />
            <div className="consulta-form__acciones">
              {proveedores.length > 1 && (
                <label className="selector-proveedor">
                  <span>Proveedor de redacción</span>
                  <select className="field" value={proveedor} onChange={(evento) => setProveedor(evento.target.value)}>
                    {proveedores.map((item) => (
                      <option key={item.id} value={item.id} disabled={item.disponible !== "si"}>
                        {item.nombre}{item.disponible !== "si" ? " · sin clave" : ""}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <button className="btn btn-primary consulta-form__boton" type="submit" disabled={ocupado || !texto.trim()}>
                <Icon name={ocupado ? "refresh" : "search"} size={16} />
                {ocupado ? "Consultando…" : "Consultar"}
              </button>
            </div>
          </form>

          <div className="lanzadores">
            <div className="lanzadores__titulo">
              <Icon name="bolt" size={15} /> Consultas de referencia
              <span className="lanzadores__pista">seleccione una para ejecutarla</span>
            </div>
            <div className="lanzadores__chips">
              {SUGERENCIAS.map((sugerencia) => (
                <button className="chip" key={sugerencia} disabled={ocupado} onClick={() => void preguntar(sugerencia)}>
                  <Icon name="search" size={12} /> {sugerencia}
                </button>
              ))}
            </div>
          </div>
        </section>

        {turnos.length > 0 && (
          <section className="resultados stack" aria-label="Resultados de las consultas">
            <div className="seccion-titulo">
              <div>
                <h2>Resultados de la sesión</h2>
                <span className="cinta" />
              </div>
              <button className="btn btn-ghost btn-sm" onClick={enfocarConsulta}>
                <Icon name="search" size={14} /> Nueva consulta
              </button>
            </div>

            {turnos.map((turno) => (
              <div key={turno.id} className="turno">
                {!turno.final && !turno.error && <Procesando turno={turno} />}
                {turno.error && (
                  <div className="aviso aviso--error">
                    <Icon name="info" size={17} />
                    <div><strong>No fue posible completar «{turno.pregunta}».</strong><br />{turno.error}</div>
                  </div>
                )}
                <TarjetaRespuesta
                  turno={turno}
                  onFeedback={(util) => marcarFeedback(turno.id, util)}
                  onSugerencia={(pregunta) => void preguntar(pregunta)}
                />
              </div>
            ))}
            <div ref={finalRef} />
          </section>
        )}

        <section id="como-funciona" className="metodologia-seccion">
          <div className="seccion-titulo seccion-titulo--simple">
            <div>
              <h2>Cómo funciona</h2>
              <p>La respuesta es útil solo si puede rastrearse hasta la consulta y los datos ejecutados.</p>
              <span className="cinta" />
            </div>
          </div>
          <div className="pasos">
            {PASOS.map((paso) => (
              <article className="paso" key={paso.titulo}>
                <div className="paso__icono">
                  <Icon name={paso.icono} size={22} />
                </div>
                <div className="paso__titulo">{paso.titulo}</div>
                <div className="paso__detalle">{paso.detalle}</div>
              </article>
            ))}
          </div>
        </section>

        <div className="avisos-finales">
          <div className="aviso aviso--advertencia">
            <Icon name="info" size={17} />
            <div><strong>La IA no sustituye la revisión técnica.</strong> Valide el periodo, las unidades, los filtros y la SQL antes de usar una cifra en documentos externos.</div>
          </div>
          <div className="aviso aviso--info">
            <Icon name="shield" size={17} />
            <div><strong>Fuente y alcance.</strong> La experiencia está configurada sobre FACT_EXPORTACIONES_SL, con valores FOB en dólares y periodicidad mensual.</div>
          </div>
        </div>
      </div>
    </>
  );
}
