/** Cliente HTTP del frontend: SSE del chat, exportables, métricas y feedback. */

import type { Celda, EventoChat, Proveedor } from "../tipos";

const sesion = (() => {
  const clave = "exportbot_session";
  let v = sessionStorage.getItem(clave);
  if (!v) {
    v = Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem(clave, v);
  }
  return v;
})();

export function sessionId(): string {
  return sesion;
}

/** POST /api/chat leyendo el stream SSE y notificando cada evento. */
export async function chatStream(
  pregunta: string,
  proveedor: string,
  onEvento: (e: EventoChat) => void,
): Promise<void> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pregunta, proveedor, session_id: sesion, historial: [] }),
  });
  if (!resp.ok || !resp.body) {
    onEvento({ tipo: "error", chat_id: "", mensaje: `Error HTTP ${resp.status} del servidor.` });
    return;
  }
  const lector = resp.body.getReader();
  const dec = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await lector.read();
    if (done) break;
    buffer += dec.decode(value, { stream: true });
    let corte: number;
    while ((corte = buffer.indexOf("\n\n")) >= 0) {
      const bloque = buffer.slice(0, corte);
      buffer = buffer.slice(corte + 2);
      const linea = bloque.split("\n").find((l) => l.startsWith("data: "));
      if (!linea) continue;
      try {
        onEvento(JSON.parse(linea.slice(6)) as EventoChat);
      } catch {
        /* bloque parcial: se ignora */
      }
    }
  }
}

export interface CuerpoExport {
  pregunta: string;
  texto: string;
  sql: string;
  columnas: string[];
  filas: Celda[][];
  chat_id: string;
}

/** Descarga Excel o PPTX construidos en el servidor. */
export async function exportar(tipo: "excel" | "pptx", cuerpo: CuerpoExport): Promise<void> {
  const resp = await fetch(`/api/exportar/${tipo}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...cuerpo, session_id: sesion }),
  });
  if (!resp.ok) throw new Error(`Exportación falló (HTTP ${resp.status}).`);
  const blob = await resp.blob();
  const disp = resp.headers.get("Content-Disposition") ?? "";
  const nombre = /filename="(.+?)"/.exec(disp)?.[1] ?? `exportbot.${tipo === "excel" ? "xlsx" : "pptx"}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombre;
  a.click();
  URL.revokeObjectURL(url);
}

export async function enviarFeedback(chatId: string, util: boolean): Promise<void> {
  await fetch("/api/track/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, util, session_id: sesion }),
  });
}

export async function listarProveedores(): Promise<Proveedor[]> {
  const r = await fetch("/api/proveedores");
  if (!r.ok) return [];
  return ((await r.json()).proveedores ?? []) as Proveedor[];
}

/** GET autenticado del panel /metricas. */
export async function metricas<T>(ruta: string, token: string): Promise<T> {
  const r = await fetch(`/api/metricas/${ruta}`, { headers: { "X-Admin-Token": token } });
  if (r.status === 401) throw new Error("Token inválido.");
  if (r.status === 503) throw new Error("Telemetría no configurada en este despliegue.");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()) as T;
}
