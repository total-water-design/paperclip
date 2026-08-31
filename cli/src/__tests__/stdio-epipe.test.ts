import { createServer } from "node:http";
import { once } from "node:events";
import { PassThrough } from "node:stream";
import { afterEach, describe, expect, it } from "vitest";
import { containStdioEpipe } from "../stdio-epipe.js";

const servers: ReturnType<typeof createServer>[] = [];

afterEach(async () => {
  await Promise.all(servers.splice(0).map(async (server) => {
    server.close();
    await once(server, "close");
  }));
});

describe("containStdioEpipe", () => {
  it("survives a deterministic output EPIPE and continues serving health traffic", async () => {
    const output = new PassThrough();
    containStdioEpipe(output);

    const server = createServer((_request, response) => {
      response.setHeader("content-type", "application/json");
      response.end(JSON.stringify({ status: "ok" }));
    });
    servers.push(server);
    server.listen(0, "127.0.0.1");
    await once(server, "listening");

    const epipe = Object.assign(new Error("write EPIPE"), { code: "EPIPE" });
    expect(() => output.emit("error", epipe)).not.toThrow();

    const address = server.address();
    if (!address || typeof address === "string") throw new Error("test server did not bind TCP");
    const response = await fetch(`http://127.0.0.1:${address.port}/api/health`);

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ status: "ok" });
  });
});
