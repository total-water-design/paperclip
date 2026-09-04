import { beforeEach, describe, expect, it, vi } from "vitest";
import { fileURLToPath } from "node:url";
import { runChildProcess } from "@paperclipai/adapter-utils/server-utils";

type ExecutionTargetRunner = typeof import("@paperclipai/adapter-utils/execution-target").runAdapterExecutionTargetProcess;

const {
  ensureAdapterExecutionTargetCommandResolvable,
  ensureAdapterExecutionTargetRuntimeCommandInstalled,
  executeCodexAcp,
  prepareCodexRuntimeConfig,
  readPaperclipRuntimeSkillEntries,
  resolveAdapterExecutionTargetCommandForLogs,
  runAdapterExecutionTargetProcess,
  tempCodexHome,
} = vi.hoisted(() => ({
  ensureAdapterExecutionTargetCommandResolvable: vi.fn(async () => undefined),
  ensureAdapterExecutionTargetRuntimeCommandInstalled: vi.fn(async () => undefined),
  executeCodexAcp: vi.fn(async () => {
    throw new Error('Transform failed with 1 error: execute.ts:818:0: ERROR: Unexpected "<<"');
  }),
  prepareCodexRuntimeConfig: vi.fn(async () => ({ cleanup: vi.fn(async () => undefined), notes: [] })),
  readPaperclipRuntimeSkillEntries: vi.fn(async () => []),
  resolveAdapterExecutionTargetCommandForLogs: vi.fn(async () => "codex"),
  runAdapterExecutionTargetProcess: vi.fn(async () => ({
    exitCode: 0,
    signal: null,
    timedOut: false,
    stdout: [
      JSON.stringify({ type: "thread.started", thread_id: "codex-thread-1" }),
      JSON.stringify({
        type: "item.completed",
        item: { type: "agent_message", text: "hello" },
      }),
      JSON.stringify({
        type: "turn.completed",
        usage: { input_tokens: 1, cached_input_tokens: 0, output_tokens: 1 },
      }),
    ].join("\n"),
    stderr: "",
    pid: 123,
    startedAt: new Date().toISOString(),
  })),
  tempCodexHome: "/tmp/paperclip-codex-acp-fallback-test-home",
}));

vi.mock("./acp.js", () => ({
  createCodexAcpExecutor: () => executeCodexAcp,
  formatCodexAcpFallbackMessage: (reason: string) =>
    `[paperclip] Codex ACP default unavailable; falling back to Codex CLI. ${reason} Set engine=acp to require ACP or engine=cli to silence this fallback.\n`,
  resolveCodexExecutionEngineForRun: async (ctx: { config: Record<string, unknown> }) =>
    ctx.config.engine === "acp"
      ? { engine: "acp", explicit: true }
      : { engine: "acp", explicit: false },
}));

vi.mock("@paperclipai/adapter-utils/execution-target", async () => {
  const actual = await vi.importActual<typeof import("@paperclipai/adapter-utils/execution-target")>(
    "@paperclipai/adapter-utils/execution-target",
  );
  return {
    ...actual,
    ensureAdapterExecutionTargetCommandResolvable,
    ensureAdapterExecutionTargetRuntimeCommandInstalled,
    resolveAdapterExecutionTargetCommandForLogs,
    runAdapterExecutionTargetProcess,
  };
});

vi.mock("@paperclipai/adapter-utils/server-utils", async () => {
  const actual = await vi.importActual<typeof import("@paperclipai/adapter-utils/server-utils")>(
    "@paperclipai/adapter-utils/server-utils",
  );
  return {
    ...actual,
    readPaperclipRuntimeSkillEntries,
  };
});

vi.mock("./codex-home.js", async () => {
  const actual = await vi.importActual<typeof import("./codex-home.js")>("./codex-home.js");
  return {
    ...actual,
    evaluateCodexCredentialReadiness: vi.fn(async () => ({
      managed: true,
      authMode: "api",
      ready: true,
      effectiveHome: tempCodexHome,
      sharedSourceHome: tempCodexHome,
    })),
    isManagedCodexHomePath: vi.fn(() => true),
    prepareManagedCodexHome: vi.fn(async () => ({ status: "seeded", home: tempCodexHome })),
    resolveManagedCodexHomeDir: vi.fn(() => tempCodexHome),
    seedManagedCodexHome: vi.fn(async () => ({ status: "seeded", home: tempCodexHome })),
  };
});

vi.mock("./runtime-config.js", async () => {
  const actual = await vi.importActual<typeof import("./runtime-config.js")>("./runtime-config.js");
  return {
    ...actual,
    prepareCodexRuntimeConfig,
  };
});

import { execute } from "./execute.js";

function buildContext(config: Record<string, unknown> = {}) {
  return {
    runId: "run-1",
    agent: {
      id: "agent-1",
      companyId: "company-1",
      name: "Codex Coder",
      adapterType: "codex_local",
      adapterConfig: {},
    },
    runtime: {
      sessionId: null,
      sessionParams: null,
      sessionDisplayId: null,
      taskKey: null,
    },
    config: {
      outputInactivityTimeoutMs: null,
      env: { OPENAI_API_KEY: "test-key" },
      ...config,
    },
    context: {},
    onLog: vi.fn(async (_stream: "stdout" | "stderr", _text: string) => {}),
  };
}

describe("codex_local ACP startup fallback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("falls back to Codex CLI when auto-selected ACP fails before execution starts", async () => {
    const ctx = buildContext({
      networkScope: "allowlist",
      networkAllowlist: ["api.openai.com"],
      filesystemSandboxCommand: "/usr/bin/bwrap",
    });

    const result = await execute(ctx as never);

    expect(result.exitCode).toBe(0);
    expect(result.summary).toBe("hello");
    expect(executeCodexAcp).toHaveBeenCalledTimes(1);
    expect(runAdapterExecutionTargetProcess).toHaveBeenCalledTimes(1);
    expect(runAdapterExecutionTargetProcess).toHaveBeenCalledWith(
      "run-1",
      null,
      "codex",
      expect.any(Array),
      expect.objectContaining({
        localProcessSandbox: expect.objectContaining({
          networkScope: "allowlist",
          networkAllowlist: ["api.openai.com"],
          command: "/usr/bin/bwrap",
        }),
      }),
    );
    expect(ctx.onLog).toHaveBeenCalledWith(
      "stderr",
      expect.stringContaining("Codex ACP startup failed"),
    );
    expect(ctx.onLog).toHaveBeenCalledWith(
      "stderr",
      expect.stringContaining('Unexpected "<<"'),
    );
  });

  it("keeps ACP fallback stdout byte-complete through confined allowlist backpressure", async () => {
    const fakeBubblewrap = fileURLToPath(
      new URL("../../../../adapter-utils/src/test-fixtures/nonblocking-bwrap.mjs", import.meta.url),
    );
    const payloadUnit = "codex-fallback-output-";
    const payloadRepetitions = 16_384;
    const payload = payloadUnit.repeat(payloadRepetitions);
    const writerScript = `const fs=require("node:fs");const payload=${JSON.stringify(payloadUnit)}.repeat(${payloadRepetitions});` +
      `const output=JSON.stringify({type:"item.completed",item:{type:"agent_message",text:payload}})+"\\n";` +
      `try { for(let offset=0;offset<output.length;offset+=4096) fs.writeSync(1,output.slice(offset,offset+4096)); } ` +
      `catch(error) { fs.writeSync(2,"failed printing to stdout: Resource temporarily unavailable (os error 11)\\n"); process.exit(101); }`;
    const fallbackRunner = runAdapterExecutionTargetProcess as unknown as {
      mockImplementationOnce: (implementation: ExecutionTargetRunner) => void;
    };
    fallbackRunner.mockImplementationOnce(async (runId, _target, _command, _args, options) =>
      runChildProcess(runId, process.execPath, ["-e", writerScript], {
        cwd: process.cwd(),
        env: options.env,
        timeoutSec: 10,
        graceSec: 1,
        localProcessSandbox: options.localProcessSandbox,
        onLog: async (stream, text) => {
          await new Promise((resolve) => setTimeout(resolve, 5));
          await options.onLog(stream, text);
        },
      }),
    );
    const ctx = buildContext({
      networkScope: "allowlist",
      networkAllowlist: ["api.openai.com"],
      filesystemSandboxCommand: fakeBubblewrap,
    });

    const result = await execute(ctx as never);

    expect(Buffer.byteLength(payload)).toBeGreaterThan(256 * 1024);
    expect(result.exitCode).toBe(0);
    expect(result.summary).toBe(payload);
    const logged = ctx.onLog.mock.calls.map(([, text]) => text).join("");
    expect(logged).not.toMatch(/EAGAIN|os error 11|failed printing to stdout/);
  });

  it("keeps explicit ACP strict when startup fails", async () => {
    const ctx = buildContext({ engine: "acp" });

    await expect(execute(ctx as never)).rejects.toThrow('Unexpected "<<"');

    expect(runAdapterExecutionTargetProcess).not.toHaveBeenCalled();
  });
});
