import { describe, expect, it } from "vitest";
import {
  createCodexFatalTransportMonitor,
  resolveCodexFatalTransportBounds,
} from "./fatal-transport-monitor.js";

class Clock {
  nowMs = 0;
  callback: (() => void) | null = null;
  now = () => this.nowMs;
  setTimer = (cb: () => void) => { this.callback = cb; return 1; };
  clearTimer = () => { this.callback = null; };
  advance(ms: number) { this.nowMs += ms; const cb = this.callback; if (cb) { this.callback = null; cb(); } }
}

function fatalPair(monitor: ReturnType<typeof createCodexFatalTransportMonitor>) {
  monitor.noteOutputChunk("stdout", '{"type":"error","message":"fatal MCP HTTP transport failure"}\n');
  monitor.noteOutputChunk("stderr", "WebSocket connection failed: proxy CONNECT response 403 after retry 5/5\n");
}

describe("Codex fatal transport monitor", () => {
  it("terminates a confirmed fatal proxy loop at the reconnect bound", () => {
    const fired: string[] = [];
    const monitor = createCodexFatalTransportMonitor({
      maxReconnects: 3,
      windowMs: 300_000,
      onFire: (state) => fired.push(state.reason ?? ""),
    });
    fatalPair(monitor);
    monitor.noteOutputChunk("stderr", "Reconnecting... waiting for network\n");
    monitor.noteOutputChunk("stderr", "Reconnecting... waiting for network\n");
    expect(fired).toEqual([]);
    monitor.noteOutputChunk("stderr", "Reconnecting... waiting for network\n");
    expect(fired).toEqual(["reconnect_limit"]);
  });

  it("also bounds a confirmed loop when reconnect wording changes", () => {
    const clock = new Clock();
    const fired: string[] = [];
    const monitor = createCodexFatalTransportMonitor({
      maxReconnects: 3,
      windowMs: 300_000,
      now: clock.now,
      setTimer: clock.setTimer,
      clearTimer: clock.clearTimer,
      onFire: (state) => fired.push(state.reason ?? ""),
    });
    fatalPair(monitor);
    clock.advance(300_000);
    expect(fired).toEqual(["time_window"]);
  });

  it("keeps ordinary transient reconnects viable without both fatal signatures", () => {
    let fired = false;
    const monitor = createCodexFatalTransportMonitor({
      maxReconnects: 2,
      windowMs: 1,
      onFire: () => { fired = true; },
    });
    monitor.noteOutputChunk("stderr", "WebSocket temporarily unavailable\nReconnecting... waiting for network\nReconnecting... waiting for network\n");
    expect(monitor.state()).toMatchObject({ armed: false, fired: false });
    monitor.stop();
    expect(fired).toBe(false);
  });

  it("uses configurable positive bounds and supports an explicit null escape hatch", () => {
    expect(resolveCodexFatalTransportBounds({ fatalTransportMaxReconnects: 7, fatalTransportWindowMs: 12_000 }))
      .toEqual({ maxReconnects: 7, windowMs: 12_000 });
    expect(resolveCodexFatalTransportBounds({ fatalTransportMaxReconnects: null })).toBeNull();
  });
});
