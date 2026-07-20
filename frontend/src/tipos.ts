/** Tipos compartidos del frontend de ExportBot 2.0. */

export type Celda = string | number | boolean | null;

export interface MetaRespuesta {
  proveedor: string;
  modelo: string;
  degradado: boolean;
  cifras_verificadas: boolean;
  latencia_analyst_ms: number;
  latencia_sql_ms: number;
  version_app: string;
  fuente_semantica: string;
  intentos: number;
}

export interface EventoFinal {
  tipo: "final";
  chat_id: string;
  texto: string;
  sql: string;
  columnas: string[];
  filas: Celda[][];
  n_filas: number;
  truncado: boolean;
  sugerencias: string[];
  meta: MetaRespuesta;
}

export interface EventoEtapa {
  tipo: "etapa";
  chat_id: string;
  etapa: string;
  detalle: string;
  sql?: string;
}

export interface EventoError {
  tipo: "error";
  chat_id: string;
  mensaje: string;
}

export type EventoChat = EventoFinal | EventoEtapa | EventoError;

export interface Turno {
  id: string;
  pregunta: string;
  etapas: EventoEtapa[];
  final?: EventoFinal;
  error?: string;
  enviandoFeedback?: boolean;
  feedback?: boolean;
}

export interface Proveedor {
  id: string;
  nombre: string;
  modelo: string;
  disponible: string;
}
