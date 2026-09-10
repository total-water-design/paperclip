import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  ConfinedArtifactTransferStore,
} from "../services/confined-artifact-transfers.js";

const MAX_BYTES = 64 * 1024 * 1024;
const binding = {
  companyId: "company-1",
  runId: "run-1",
  agentId: "agent-1",
  issueId: "issue-1",
};

function sha256(bytes: Buffer) {
  return createHash("sha256").update(bytes).digest("hex");
}

describe("ConfinedArtifactTransferStore", () => {
  let rootDir: string;
  let store: ConfinedArtifactTransferStore;

  beforeEach(async () => {
    rootDir = await fs.mkdtemp(path.join(os.tmpdir(), "paperclip-confined-transfer-test-"));
    store = new ConfinedArtifactTransferStore({
      maxBytes: MAX_BYTES,
      rootDir,
      chunkBytes: 4,
      ttlMs: 60_000,
    });
  });

  afterEach(async () => {
    await store.close();
  });

  async function begin(bytes: Buffer, overrides: Partial<Parameters<typeof store.begin>[0]> = {}) {
    return store.begin({
      ...binding,
      originalFilename: "evidence.bin",
      contentType: "application/octet-stream",
      byteSize: bytes.length,
      sha256: sha256(bytes),
      ...overrides,
    });
  }

  it("preserves exact bytes, content type, filename, and sha256 across ordered chunks", async () => {
    const bytes = Buffer.from([0, 255, 1, 2, 128, 13, 10]);
    const transfer = await begin(bytes, {
      originalFilename: "résumé.bin",
      contentType: "application/x-test",
    });

    await expect(
      store.appendChunk(transfer.transferId, binding, {
        index: 0,
        data: bytes.subarray(0, 4).toString("base64"),
      }),
    ).resolves.toEqual({ nextIndex: 1, receivedBytes: 4 });
    await store.appendChunk(transfer.transferId, binding, {
      index: 1,
      data: bytes.subarray(4).toString("base64"),
    });

    const completed = await store.complete(transfer.transferId, binding);
    expect(completed).toMatchObject({
      originalFilename: "résumé.bin",
      contentType: "application/x-test",
      byteSize: bytes.length,
      sha256: sha256(bytes),
    });
    expect(completed.body).toEqual(bytes);
    await expect(store.complete(transfer.transferId, binding)).rejects.toMatchObject({
      status: 404,
      code: "transfer_not_found",
    });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it("accepts the 64 MiB policy boundary and rejects one byte over it without allocating the body", async () => {
    const atLimit = await store.begin({
      ...binding,
      originalFilename: "boundary.bin",
      contentType: "application/octet-stream",
      byteSize: MAX_BYTES,
      sha256: "a".repeat(64),
    });
    expect(atLimit.chunkBytes).toBe(4);
    await store.abort(atLimit.transferId, binding);

    await expect(
      store.begin({
        ...binding,
        originalFilename: "too-large.bin",
        contentType: "application/octet-stream",
        byteSize: MAX_BYTES + 1,
        sha256: "a".repeat(64),
      }),
    ).rejects.toMatchObject({
      status: 422,
      code: "attachment_too_large",
    });
  });

  it.each([
    ["../escape.bin", "application/octet-stream", "unsafe_filename"],
    ["escape\\file.bin", "application/octet-stream", "unsafe_filename"],
    ["safe.bin", "text/plain\r\nx-injected: yes", "invalid_content_type"],
  ])("rejects unsafe filename or content-type metadata", async (originalFilename, contentType, code) => {
    await expect(
      store.begin({
        ...binding,
        originalFilename,
        contentType,
        byteSize: 1,
        sha256: sha256(Buffer.from("x")),
      }),
    ).rejects.toMatchObject({ status: 422, code });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it("rejects malformed base64 and removes the partial transfer", async () => {
    const transfer = await begin(Buffer.from("abc"));
    await expect(
      store.appendChunk(transfer.transferId, binding, { index: 0, data: "ab c" }),
    ).rejects.toMatchObject({ status: 422, code: "malformed_chunk" });
    await expect(store.complete(transfer.transferId, binding)).rejects.toMatchObject({
      status: 404,
      code: "transfer_not_found",
    });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it.each([
    ["duplicated", 0],
    ["out-of-order", 2],
  ])("rejects a %s chunk and removes the transfer", async (_label, invalidIndex) => {
    const bytes = Buffer.from("abcdef");
    const transfer = await begin(bytes);
    await store.appendChunk(transfer.transferId, binding, {
      index: 0,
      data: bytes.subarray(0, 4).toString("base64"),
    });

    await expect(
      store.appendChunk(transfer.transferId, binding, {
        index: invalidIndex,
        data: bytes.subarray(4).toString("base64"),
      }),
    ).rejects.toMatchObject({ status: 409, code: "chunk_out_of_order" });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it("rejects a short non-final chunk and removes the transfer", async () => {
    const bytes = Buffer.from("abcdef");
    const transfer = await begin(bytes);
    await expect(
      store.appendChunk(transfer.transferId, binding, {
        index: 0,
        data: bytes.subarray(0, 2).toString("base64"),
      }),
    ).rejects.toMatchObject({ status: 422, code: "invalid_chunk_size" });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it("rejects an incomplete completion and removes the transfer", async () => {
    const bytes = Buffer.from("abcdef");
    const transfer = await begin(bytes);
    await store.appendChunk(transfer.transferId, binding, {
      index: 0,
      data: bytes.subarray(0, 4).toString("base64"),
    });

    await expect(store.complete(transfer.transferId, binding)).rejects.toMatchObject({
      status: 409,
      code: "incomplete_transfer",
    });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it("rejects same-length spool tampering before publication", async () => {
    const bytes = Buffer.from("abcd");
    const transfer = await begin(bytes);
    await store.appendChunk(transfer.transferId, binding, {
      index: 0,
      data: bytes.toString("base64"),
    });
    const [spoolName] = await fs.readdir(rootDir);
    await fs.writeFile(path.join(rootDir, spoolName!), Buffer.from("wxyz"));

    await expect(store.complete(transfer.transferId, binding)).rejects.toMatchObject({
      status: 422,
      code: "sha256_mismatch",
    });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it("rejects a mismatched whole-file hash and removes the transfer", async () => {
    const bytes = Buffer.from("abcd");
    const transfer = await begin(bytes, { sha256: "0".repeat(64) });
    await store.appendChunk(transfer.transferId, binding, {
      index: 0,
      data: bytes.toString("base64"),
    });

    await expect(store.complete(transfer.transferId, binding)).rejects.toMatchObject({
      status: 422,
      code: "sha256_mismatch",
    });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
  });

  it("conceals binding mismatches without destroying the authorized transfer", async () => {
    const bytes = Buffer.from("abcd");
    const transfer = await begin(bytes);

    for (const mismatch of [
      { ...binding, companyId: "company-2" },
      { ...binding, runId: "run-2" },
      { ...binding, agentId: "agent-2" },
      { ...binding, issueId: "issue-2" },
    ]) {
      await expect(
        store.appendChunk(transfer.transferId, mismatch, {
          index: 0,
          data: bytes.toString("base64"),
        }),
      ).rejects.toMatchObject({ status: 404, code: "transfer_not_found" });
    }

    await store.appendChunk(transfer.transferId, binding, {
      index: 0,
      data: bytes.toString("base64"),
    });
    await expect(store.complete(transfer.transferId, binding)).resolves.toMatchObject({
      body: bytes,
    });
  });

  it("expires and cleans incomplete transfers", async () => {
    let nowMs = 1_000;
    await store.close();
    store = new ConfinedArtifactTransferStore({
      maxBytes: MAX_BYTES,
      rootDir,
      chunkBytes: 4,
      ttlMs: 50,
      now: () => nowMs,
    });
    const expiryBytes = Buffer.from("abcdef");
    const transfer = await begin(expiryBytes);
    await store.appendChunk(transfer.transferId, binding, {
      index: 0,
      data: expiryBytes.subarray(0, 4).toString("base64"),
    });

    nowMs += 51;
    await expect(store.complete(transfer.transferId, binding)).rejects.toMatchObject({
      status: 410,
      code: "transfer_expired",
    });
    await expect(fs.readdir(rootDir)).resolves.toEqual([]);
    await expect(store.sweepExpired()).resolves.toBe(0);
  });
});
