import fs from "node:fs/promises";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildLocalProcessSandboxSpawnTarget } from "./local-process-sandbox.js";

function epipe(): NodeJS.ErrnoException {
  return Object.assign(new Error("write EPIPE"), {
    code: "EPIPE",
    errno: -32,
    syscall: "write",
  });
}

function proxySocketPath(target: Awaited<ReturnType<typeof buildLocalProcessSandboxSpawnTarget>>): string {
  const bridgeIndex = target.args.findIndex((value) => value.endsWith("/bridge.cjs"));
  if (bridgeIndex < 0 || !target.args[bridgeIndex + 1]) throw new Error("Proxy socket path not found in sandbox target.");
  return target.args[bridgeIndex + 1];
}

async function rawConnect(socketPath: string, authority: string): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    let connected = false;
    let settled = false;
    const socket = net.createConnection(socketPath);
    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error) reject(error);
      else resolve();
    };
    const timer = setTimeout(() => {
      socket.destroy();
      finish(new Error(`Timed out waiting for CONNECT ${authority} to close.`));
    }, 2_000);

    socket.once("connect", () => {
      connected = true;
      socket.end(`CONNECT ${authority} HTTP/1.1\r\nHost: ${authority}\r\n\r\n`);
    });
    socket.resume();
    socket.once("error", (error) => {
      if (connected) finish();
      else finish(error);
    });
    socket.once("close", () => finish());
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("local process sandbox CONNECT client lifecycle", () => {
  it("contains EPIPE while writing a denied CONNECT response", async () => {
    const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-connect-deny-epipe-"));
    const target = await buildLocalProcessSandboxSpawnTarget({
      executable: process.execPath,
      args: ["-e", "process.exit(0)"],
      cwd: workspace,
      options: {
        workspaceDir: workspace,
        networkScope: "allowlist",
        networkAllowlist: ["allowed.invalid:443"],
      },
    });
    const socketPath = proxySocketPath(target);
    const originalEnd = net.Socket.prototype.end;
    let injected = false;

    vi.spyOn(net.Socket.prototype, "end").mockImplementation(function (this: net.Socket, ...args: any[]) {
      const result = Reflect.apply(originalEnd, this, args);
      if (typeof args[0] === "string" && args[0].startsWith("HTTP/1.1 403 Forbidden")) {
        injected = true;
        queueMicrotask(() => this.emit("error", epipe()));
      }
      return result;
    } as any);

    try {
      await rawConnect(socketPath, "example.com:443");
      await new Promise<void>((resolve) => setImmediate(resolve));
      expect(injected).toBe(true);
    } finally {
      await target.cleanup?.();
      await fs.rm(workspace, { recursive: true, force: true });
    }
  });

  it("contains EPIPE while writing the successful CONNECT 200 response", async () => {
    const workspace = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-connect-success-epipe-"));
    const upstreamServer = net.createServer((socket) => socket.resume());
    await new Promise<void>((resolve) => upstreamServer.listen(0, "127.0.0.1", resolve));
    const address = upstreamServer.address();
    if (!address || typeof address === "string") throw new Error("Expected TCP test server address.");

    const target = await buildLocalProcessSandboxSpawnTarget({
      executable: process.execPath,
      args: ["-e", "process.exit(0)"],
      cwd: workspace,
      options: {
        workspaceDir: workspace,
        networkScope: "allowlist",
        networkAllowlist: [`127.0.0.1:${address.port}`],
      },
    });
    const socketPath = proxySocketPath(target);
    const originalWrite = net.Socket.prototype.write;
    let injected = false;

    vi.spyOn(net.Socket.prototype, "write").mockImplementation(function (this: net.Socket, ...args: any[]) {
      const result = Reflect.apply(originalWrite, this, args);
      if (args[0] === "HTTP/1.1 200 Connection Established\r\n\r\n") {
        injected = true;
        queueMicrotask(() => this.emit("error", epipe()));
      }
      return result;
    } as any);

    try {
      await rawConnect(socketPath, `127.0.0.1:${address.port}`);
      await new Promise<void>((resolve) => setImmediate(resolve));
      expect(injected).toBe(true);
    } finally {
      await target.cleanup?.();
      await new Promise<void>((resolve) => upstreamServer.close(() => resolve()));
      await fs.rm(workspace, { recursive: true, force: true });
    }
  });
});
