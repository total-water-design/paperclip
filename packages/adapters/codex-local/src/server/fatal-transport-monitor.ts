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

function isStructuredReconnectWaitingError(line: string): boolean {
  const parsed = parseJson(line.trim());
  if (!parsed || typeof parsed !== "object") return false;
  const record = parsed as Record<string, unknown>;
  return record.type === "error" &&
    typeof record.message === "string" &&
    /^Reconnecting\.\.\. waiting for network \([^)]+\)$/.test(record.message);
}

const RMCP_FATAL_CHANNEL_CLOSED_RE =
  /rmcp::transport::worker:\s*worker quit with fatal:\s*Transport channel closed\b/i;
const WEBSOCKET_PROXY_CONNECT_403_RE =
  /WebSocket\s+Proxy connection failed:\s*HTTP CONNECT failed with status 403\b/i;

export function createCodexFatalTransportMonitor(
  options: CodexFatalTransportMonitorOptions,
): CodexFatalTransportMonitorHandle {
  const now = options.now ?? (() => Date.now());
  const setTimer = options.setTimer ?? ((cb, ms) => setTimeout(cb, ms));
  const clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle as ReturnType<typeof setTimeout>));
  let stdoutBuffer = "";
  let stderrEvidence = "";
  let sawRmcpFatalChannelClosed = false;
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
    if (stopped || state.armed || !sawRmcpFatalChannelClosed || !sawProxy403) return;
    state.armed = true;
    state.armedAt = now();
    timer = setTimer(() => fire("time_window"), options.windowMs);
  };
  const noteReconnectLines = (lines: string[]) => {
    if (!state.armed || state.fired) return;
    state.reconnectCount += lines.filter(isStructuredReconnectWaitingError).length;
    if (state.reconnectCount >= options.maxReconnects) fire("reconnect_limit");
  };

  return {
    noteOutputChunk(stream, chunk) {
      if (stopped || state.fired || !chunk) return;
      if (stream === "stdout") {
        stdoutBuffer += chunk;
        const lines = stdoutBuffer.split(/\r?\n/);
        stdoutBuffer = lines.pop() ?? "";
        maybeArm();
        noteReconnectLines(lines);
      } else {
        stderrEvidence = `${stderrEvidence}${chunk}`.slice(-16_384);
        sawRmcpFatalChannelClosed ||= RMCP_FATAL_CHANNEL_CLOSED_RE.test(stderrEvidence);
        sawProxy403 ||= WEBSOCKET_PROXY_CONNECT_403_RE.test(stderrEvidence);
        maybeArm();
      }
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
