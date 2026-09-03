import { parseJson } from "@paperclipai/adapter-utils/server-utils";

export const DEFAULT_CODEX_FATAL_TRANSPORT_MAX_RECONNECTS = 3;
export const DEFAULT_CODEX_FATAL_TRANSPORT_WINDOW_MS = 5 * 60 * 1000;

export interface CodexFatalTransportMonitorOptions {
  maxReconnects: number;
  windowMs: number;
  onFire: (state: CodexFatalTransportMonitorState) => void;
  now?: () => number;
  setTimer?: (cb: () => void, ms: number) => unknown;
  clearTimer?: (handle: unknown) => void;
}

export interface CodexFatalTransportMonitorState {
  armed: boolean;
  fired: boolean;
  armedAt: number | null;
  firedAt: number | null;
  reconnectCount: number;
  reason: "reconnect_limit" | "time_window" | null;
}

export interface CodexFatalTransportMonitorHandle {
  noteOutputChunk(stream: "stdout" | "stderr", chunk: string): void;
  state(): CodexFatalTransportMonitorState;
  stop(): CodexFatalTransportMonitorState;
}

export function resolveCodexFatalTransportBounds(config: {
  fatalTransportMaxReconnects?: unknown;
  fatalTransportWindowMs?: unknown;
}): { maxReconnects: number; windowMs: number } | null {
  if (config.fatalTransportMaxReconnects === null || config.fatalTransportWindowMs === null) return null;
  const maxReconnects =
    typeof config.fatalTransportMaxReconnects === "number" &&
    Number.isFinite(config.fatalTransportMaxReconnects) &&
    config.fatalTransportMaxReconnects > 0
      ? Math.floor(config.fatalTransportMaxReconnects)
      : DEFAULT_CODEX_FATAL_TRANSPORT_MAX_RECONNECTS;
  const windowMs =
    typeof config.fatalTransportWindowMs === "number" &&
    Number.isFinite(config.fatalTransportWindowMs) &&
    config.fatalTransportWindowMs > 0
      ? config.fatalTransportWindowMs
      : DEFAULT_CODEX_FATAL_TRANSPORT_WINDOW_MS;
  return { maxReconnects, windowMs };
}

function objectStrings(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(objectStrings);
  if (value && typeof value === "object") return Object.values(value).flatMap(objectStrings);
  return [];
}

function isStructuredFatalTransportError(line: string): boolean {
  const parsed = parseJson(line.trim());
  if (!parsed || typeof parsed !== "object") return false;
  const record = parsed as Record<string, unknown>;
  const type = typeof record.type === "string" ? record.type : "";
  const text = objectStrings(record).join(" ");
  return /error|failed|fatal/i.test(type) && /fatal/i.test(text) && /mcp|http|transport/i.test(text);
}

export function createCodexFatalTransportMonitor(
  options: CodexFatalTransportMonitorOptions,
): CodexFatalTransportMonitorHandle {
  const now = options.now ?? (() => Date.now());
  const setTimer = options.setTimer ?? ((cb, ms) => setTimeout(cb, ms));
  const clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));
  let stdoutBuffer = "";
  let stderrEvidence = "";
  let sawStructuredFatal = false;
  let sawProxy403 = false;
  let stopped = false;
  let timer: unknown = null;
  const state: CodexFatalTransportMonitorState = {
    armed: false,
    fired: false,
    armedAt: null,
    firedAt: null,
    reconnectCount: 0,
    reason: null,
  };

  const fire = (reason: "reconnect_limit" | "time_window") => {
    if (stopped || state.fired) return;
    state.fired = true;
    state.firedAt = now();
    state.reason = reason;
    if (timer != null) clearTimer(timer);
    timer = null;
    options.onFire({ ...state });
  };
  const maybeArm = () => {
    if (stopped || state.armed || !sawStructuredFatal || !sawProxy403) return;
    state.armed = true;
    state.armedAt = now();
    timer = setTimer(() => fire("time_window"), options.windowMs);
  };
  const noteReconnects = (chunk: string) => {
    if (!state.armed || state.fired) return;
    const matches = chunk.match(/Reconnecting\.\.\.\s*waiting for network/gi);
    state.reconnectCount += matches?.length ?? 0;
    if (state.reconnectCount >= options.maxReconnects) fire("reconnect_limit");
  };

  return {
    noteOutputChunk(stream, chunk) {
      if (stopped || state.fired || !chunk) return;
      if (stream === "stdout") {
        stdoutBuffer += chunk;
        const lines = stdoutBuffer.split(/\r?\n/);
        stdoutBuffer = lines.pop() ?? "";
        if (lines.some(isStructuredFatalTransportError)) sawStructuredFatal = true;
      } else {
        stderrEvidence = `${stderrEvidence}${chunk}`.slice(-16_384);
        sawProxy403 =
          /websocket/i.test(stderrEvidence) &&
          /(?:proxy\s+)?connect[^\r\n]*\b403\b|\b403\b[^\r\n]*proxy/i.test(stderrEvidence);
      }
      maybeArm();
      noteReconnects(chunk);
    },
    state: () => ({ ...state }),
    stop() {
      stopped = true;
      if (timer != null) clearTimer(timer);
      timer = null;
      return { ...state };
    },
  };
}

export function formatCodexFatalTransportError(state: CodexFatalTransportMonitorState): string {
  return `fatal Codex proxy/transport failure persisted (${state.reconnectCount} reconnects; bound=${state.reason})`;
}
