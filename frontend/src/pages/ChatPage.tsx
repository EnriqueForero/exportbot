/** Página de chat de ExportBot 2.0: pregunta → etapas → tarjeta verificable. */

import { FormEvent, useEffect, useRef, useState } from "react";
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

const NUM = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 2 });

function esNumero(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function Tabla({ final }: { final: EventoFinal }) {
  if (!final.columnas.length) return null;
  return (
    <>
      <div className="tabla-envoltura">
        <table className="datos">
          <thead>
            <tr>{final.columnas.map((c) => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {final.filas.map((fila, i) => (
              <tr key={i}>
                {fila.map((v, j) => (
                  <td key={j} className={esNumero(v) ? "num" : undefined}>
                    {v === null ? "—" : esNumero(v) ? NUM.format(v) : String(v)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {final.truncado && (
        <div className="nota-truncado">
          Mostrando {final.filas.length} de {final.n_filas} filas (resultado truncado al tope
          configurado). El Excel descarga lo que ve en pantalla.
        </div>
      )}
    </>
  );
}

function Tarjeta({ turno, onFeedback }: { turno: Turno; onFeedback: (util: boolean) => void }) {
  const f = turno.final;
  const [exportando, setExportando] = useState<"" | "excel" | "pptx">("");
  if (!f) return null;

  const descargar = async (tipo: "excel" | "pptx") => {
    setExportando(tipo);
    try {
      await exportar(tipo, {
        pregunta: turno.pregunta,
        texto: f.texto,
        sql: f.sql,
        columnas: f.columnas,
        filas: f.filas,
        chat_id: f.chat_id,
      });
    } catch (e) {
      alert(e instanceof Error ? e.message : "No se pudo exportar.");
    } finally {
      setExportando("");
    }
  };

  return (
    <div className="tarjeta">
      <div className="texto">{f.texto}</div>
      <div className="chips">
        <span className="chip">Snowflake · {f.n_filas} fila(s)</span>
        <span className="chip">SQL {f.meta.latencia_sql_ms} ms · Analyst {f.meta.latencia_analyst_ms} ms</span>
        <span className="chip">Redacción: {f.meta.proveedor}{f.meta.modelo ? ` · ${f.meta.modelo}` : ""}</span>
        <span className={`chip ${f.meta.cifras_verificadas ? "ok" : "warn"}`}>
          {f.meta.cifras_verificadas ? "Cifras verificadas contra el resultado" : "Redacción degradada a plantilla"}
        </span>
        {f.meta.intentos > 1 && <span className="chip">SQL corregida ({f.meta.intentos} intentos)</span>}
      </div>
      {f.sql && (
        <details className="sql">
          <summary>Ver SQL ejecutada (trazabilidad)</summary>
          <pre>{f.sql}</pre>
        </details>
      )}
      <Tabla final={f} />
      <div className="acciones">
        {f.columnas.length > 0 && (
          <>
            <button className="primario" disabled={exportando !== ""} onClick={() => descargar("excel")}>
              {exportando === "excel" ? "Generando…" : "Descargar Excel"}
            </button>
            <button disabled={exportando !== ""} onClick={() => descargar("pptx")}>
              {exportando === "pptx" ? "Generando…" : "Descargar presentación"}
            </button>
          </>
        )}
        <div className="fb" title="¿Le fue útil esta respuesta? Alimenta la auditoría de calidad.">
          <button
            className={turno.feedback === true ? "activo" : ""}
            disabled={turno.feedback !== undefined}
            onClick={() => onFeedback(true)}
          >
            👍
          </button>
          <button
            className={turno.feedback === false ? "activo" : ""}
            disabled={turno.feedback !== undefined}
            onClick={() => onFeedback(false)}
          >
            👎
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [proveedor, setProveedor] = useState("cortex");
  const finalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listarProveedores().then(setProveedores).catch(() => setProveedores([]));
  }, []);
  useEffect(() => {
    finalRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turnos]);

  const preguntar = async (pregunta: string) => {
    const limpia = pregunta.trim();
    if (!limpia || ocupado) return;
    setOcupado(true);
    setTexto("");
    const id = Math.random().toString(36).slice(2);
    setTurnos((t) => [...t, { id, pregunta: limpia, etapas: [] }]);
    const actualizar = (fn: (t: Turno) => Turno) =>
      setTurnos((lista) => lista.map((t) => (t.id === id ? fn(t) : t)));
    try {
      await chatStream(limpia, proveedor, (ev) => {
        if (ev.tipo === "etapa") actualizar((t) => ({ ...t, etapas: [...t.etapas, ev] }));
        else if (ev.tipo === "final") actualizar((t) => ({ ...t, final: ev }));
        else actualizar((t) => ({ ...t, error: ev.mensaje }));
      });
    } catch {
      actualizar((t) => ({ ...t, error: "Se perdió la conexión con el servidor." }));
    } finally {
      setOcupado(false);
    }
  };

  const manejarEnvio = (e: FormEvent) => {
    e.preventDefault();
    void preguntar(texto);
  };

  const marcarFeedback = (id: string, util: boolean) => {
    setTurnos((lista) => lista.map((t) => (t.id === id ? { ...t, feedback: util } : t)));
    const turno = turnos.find((t) => t.id === id);
    if (turno?.final) void enviarFeedback(turno.final.chat_id, util);
  };

  return (
    <div className="lienzo">
      {turnos.length === 0 && (
        <section className="hero">
          <h2>Pregúntele a la base de exportaciones de Colombia</h2>
          <p>
            ExportBot convierte su pregunta en una consulta verificable sobre Snowflake
            (Cortex Analyst), muestra la SQL y los datos de origen, y deja todo auditado.
          </p>
          <span className="corte">Fuente: FACT_EXPORTACIONES_SL · mensual 2006-01 a 2026-04 · USD FOB</span>
        </section>
      )}
      {turnos.length === 0 && (
        <div className="sugerencias">
          {SUGERENCIAS.map((s) => (
            <button key={s} onClick={() => void preguntar(s)} disabled={ocupado}>
              {s}
            </button>
          ))}
        </div>
      )}

      {turnos.map((t) => (
        <div className="turno" key={t.id}>
          <div style={{ textAlign: "right" }}>
            <span className="pregunta">{t.pregunta}</span>
          </div>
          {!t.final && !t.error && (
            <ul className="etapas">
              {t.etapas.map((e, i) => (
                <li key={i}>{e.detalle}</li>
              ))}
              <li>…</li>
            </ul>
          )}
          {t.error && <div className="error-caja">{t.error}</div>}
          <Tarjeta turno={t} onFeedback={(u) => marcarFeedback(t.id, u)} />
        </div>
      ))}
      <div ref={finalRef} />

      <div className="entrada">
        <form onSubmit={manejarEnvio}>
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Ej.: ¿Cuánto exportó Antioquia a Estados Unidos en 2025?"
            maxLength={800}
            disabled={ocupado}
          />
          {proveedores.length > 1 && (
            <select value={proveedor} onChange={(e) => setProveedor(e.target.value)} title="Proveedor de redacción">
              {proveedores.map((p) => (
                <option key={p.id} value={p.id} disabled={p.disponible !== "si"}>
                  {p.nombre}{p.disponible !== "si" ? " (sin clave)" : ""}
                </option>
              ))}
            </select>
          )}
          <button type="submit" disabled={ocupado || !texto.trim()}>
            {ocupado ? "Consultando…" : "Preguntar"}
          </button>
        </form>
      </div>
    </div>
  );
}
