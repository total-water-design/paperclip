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

function retainedIncidentPair(monitor: ReturnType<typeof createCodexFatalTransportMonitor>) {
  monitor.noteOutputChunk("stderr", "2026-08-31T04:18:22Z ERROR rmcp::transport::wor");
  monitor.noteOutputChunk("stderr", "ker: worker quit with fatal: Transport channel closed while polling\nWebSocket Proxy con");
  monitor.noteOutputChunk("stderr", "nection failed: HTTP CONNECT failed with status 403\n");
}

describe("Codex fatal transport monitor", () => {
  it("terminates a confirmed fatal proxy loop at the reconnect bound", () => {
    const fired: string[] = [];
    const monitor = createCodexFatalTransportMonitor({
      maxReconnects: 3,
      windowMs: 300_000,
      onFire: (state) => fired.push(state.reason ?? ""),
    });
    retainedIncidentPair(monitor);
    monitor.noteOutputChunk("stdout", "Reconnecting 2/5\nReconnecting 3/5\nUsing HTTPS fallback\n");
    monitor.noteOutputChunk("stdout", '{"type":"error","message":"Reconnecting... waiting for net');
    monitor.noteOutputChunk("stdout", 'work (attempt 3/5)"}\n{"type":"error","message":"Reconnecting... waiting for network (attempt 4/5)"}\n');
    expect(fired).toEqual([]);
    monitor.noteOutputChunk("stdout", '{"type":"error","message":"Reconnecting... waiting for network (attempt 5/5)"}\n');
    expect(fired).toEqual(["reconnect_limit"]);
    expect(monitor.state()).toMatchObject({ armed: true, fired: true, reconnectCount: 3 });
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
    retainedIncidentPair(monitor);
    clock.advance(300_000);
    expect(fired).toEqual(["time_window"]);
  });

  it("cancels the deadline on stop and ignores late output after firing", () => {
    const clock = new Clock();
    let fireCount = 0;
    const stoppedMonitor = createCodexFatalTransportMonitor({
      maxReconnects: 1,
      windowMs: 300_000,
      now: clock.now,
      setTimer: clock.setTimer,
      clearTimer: clock.clearTimer,
      onFire: () => { fireCount += 1; },
    });
    retainedIncidentPair(stoppedMonitor);
    expect(stoppedMonitor.stop()).toMatchObject({ armed: true, fired: false });
    clock.advance(300_000);
    expect(fireCount).toBe(0);

    const firedMonitor = createCodexFatalTransportMonitor({
      maxReconnects: 1,
      windowMs: 300_000,
      onFire: () => { fireCount += 1; },
    });
    retainedIncidentPair(firedMonitor);
    firedMonitor.noteOutputChunk("stdout", '{"type":"error","message":"Reconnecting... waiting for network (attempt 5/5)"}\n');
    firedMonitor.noteOutputChunk("stdout", '{"type":"error","message":"Reconnecting... waiting for network (attempt 5/5)"}\n');
    expect(fireCount).toBe(1);
    expect(firedMonitor.state()).toMatchObject({ fired: true, reason: "reconnect_limit", reconnectCount: 1 });
    firedMonitor.stop();
  });

  it.each([
    ["only the RMCP fatal signature", "rmcp::transport::worker: worker quit with fatal: Transport channel closed\n"],
    ["only the proxy signature", "WebSocket Proxy connection failed: HTTP CONNECT failed with status 403\n"],
    ["a generic HTTP 403", "request failed with HTTP status 403\n"],
  ])("does not arm for %s", (_label, stderr) => {
    let fired = false;
    const monitor = createCodexFatalTransportMonitor({
      maxReconnects: 2,
      windowMs: 1,
      onFire: () => { fired = true; },
    });
    monitor.noteOutputChunk("stderr", stderr);
    monitor.noteOutputChunk("stdout", '{"type":"error","message":"Reconnecting... waiting for network (attempt 4/5)"}\n');
    monitor.noteOutputChunk("stdout", '{"type":"error","message":"Reconnecting... waiting for network (attempt 5/5)"}\n');
    expect(monitor.state()).toMatchObject({ armed: false, fired: false });
    monitor.stop();
    expect(fired).toBe(false);
  });

  it("keeps ordinary transient reconnects viable", () => {
    let fired = false;
    const monitor = createCodexFatalTransportMonitor({ maxReconnects: 1, windowMs: 1, onFire: () => { fired = true; } });
    monitor.noteOutputChunk("stderr", "WebSocket temporarily unavailable\n");
    monitor.noteOutputChunk("stdout", "Reconnecting... waiting for network\n");
    expect(monitor.stop()).toMatchObject({ armed: false, fired: false, reconnectCount: 0 });
    expect(fired).toBe(false);
  });

  it("uses configurable positive bounds and supports an explicit null escape hatch", () => {
    expect(resolveCodexFatalTransportBounds({ fatalTransportMaxReconnects: 7, fatalTransportWindowMs: 12_000 }))
      .toEqual({ maxReconnects: 7, windowMs: 12_000 });
    expect(resolveCodexFatalTransportBounds({ fatalTransportMaxReconnects: null })).toBeNull();
  });
});
