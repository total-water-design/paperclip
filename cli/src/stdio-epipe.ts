import type { Writable } from "node:stream";

type WritableWithErrorEvents = Pick<Writable, "on">;

function isBrokenPipe(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && error.code === "EPIPE";
}

/**
 * Prevent a disconnected stdout/stderr consumer from taking down the foreground
 * `paperclipai run` process. Other stream failures keep Node's normal fatal
 * behavior; only EPIPE is contained.
 */
export function containStdioEpipe(stream: WritableWithErrorEvents): void {
  stream.on("error", (error: unknown) => {
    if (isBrokenPipe(error)) return;

    // Adding an error listener changes EventEmitter's default throw behavior.
    // Re-throw non-EPIPE errors so this guard does not hide unrelated failures.
    queueMicrotask(() => {
      throw error;
    });
  });
}

export function containProcessStdioEpipe(): void {
  containStdioEpipe(process.stdout);
  containStdioEpipe(process.stderr);
}
