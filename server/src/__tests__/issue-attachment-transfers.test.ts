import { createHash } from "node:crypto";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  assembleAttachmentTransfer,
  attachmentTransferExpired,
  claimAttachmentTransfer,
  createAttachmentTransfer,
  readAttachmentTransfer,
  sweepExpiredAttachmentTransfers,
  writeAttachmentTransferChunk,
} from "../services/issue-attachment-transfers.js";

const sha256 = (bytes: Buffer) => createHash("sha256").update(bytes).digest("hex");

async function fixture(bytes: Buffer, chunkSize = 4, now = new Date("2026-01-01T00:00:00Z")) {
  const root = await mkdtemp(path.join(tmpdir(), "attachment-transfer-"));
  const manifest = await createAttachmentTransfer(root, {
    companyId: "company-a",
    issueId: "issue-a",
    agentId: "agent-a",
    runId: "run-a",
    originalFilename: "proof.bin",
    contentType: "application/octet-stream",
    totalBytes: bytes.length,
    sha256: sha256(bytes),
    chunkSize,
    issueCommentId: null,
  }, now);
  return { root, manifest };
}

describe("confined attachment transfer spool", () => {
  it("rejects malformed ordering and exact-byte mismatches", async () => {
    const bytes = Buffer.from("abcdefgh");
    const { root, manifest } = await fixture(bytes);
    await expect(writeAttachmentTransferChunk(root, manifest, 1, bytes.subarray(4))).rejects.toThrow("in order");
    await expect(writeAttachmentTransferChunk(root, manifest, 0, Buffer.from("abc"))).rejects.toThrow("exactly 4 bytes");
  });

  it("keeps incomplete transfers unclaimable", async () => {
    const bytes = Buffer.from("abcdefgh");
    const { root, manifest } = await fixture(bytes);
    const next = await writeAttachmentTransferChunk(root, manifest, 0, bytes.subarray(0, 4));
    await expect(claimAttachmentTransfer(root, next)).resolves.toBeNull();
  });

  it("assembles byte-identical content and reports its exact hash", async () => {
    const bytes = Buffer.from("abcdefghij");
    const { root, manifest } = await fixture(bytes);
    let current = manifest;
    for (let index = 0; index < manifest.totalChunks; index += 1) {
      current = await writeAttachmentTransferChunk(
        root,
        current,
        index,
        bytes.subarray(index * manifest.chunkSize, Math.min((index + 1) * manifest.chunkSize, bytes.length)),
      );
    }
    const claimed = await claimAttachmentTransfer(root, current);
    expect(claimed).not.toBeNull();
    const assembled = await assembleAttachmentTransfer(root, claimed!);
    expect(assembled.bytes.equals(bytes)).toBe(true);
    expect(assembled.byteCount).toBe(bytes.length);
    expect(assembled.sha256).toBe(sha256(bytes));
  });

  it("detects an assembled hash mismatch after spool tampering", async () => {
    const bytes = Buffer.from("abcdefgh");
    const { root, manifest } = await fixture(bytes);
    let current = await writeAttachmentTransferChunk(root, manifest, 0, bytes.subarray(0, 4));
    current = await writeAttachmentTransferChunk(root, current, 1, bytes.subarray(4));
    await writeFile(path.join(root, manifest.id, "chunk-1"), Buffer.from("WXYZ"));
    const assembled = await assembleAttachmentTransfer(root, current);
    expect(assembled.byteCount).toBe(bytes.length);
    expect(assembled.sha256).not.toBe(manifest.sha256);
  });

  it("expires and sweeps transfers without publishing them", async () => {
    const { root, manifest } = await fixture(Buffer.from("data"));
    const afterExpiry = new Date("2026-01-02T00:00:01Z");
    expect(attachmentTransferExpired(manifest, afterExpiry)).toBe(true);
    expect(await sweepExpiredAttachmentTransfers(root, afterExpiry)).toBe(1);
    await expect(readFile(path.join(root, manifest.id, "manifest.json"))).rejects.toThrow();
  });

  it("persists run, agent, issue, company, and declared metadata", async () => {
    const { root, manifest } = await fixture(Buffer.from("data"));
    await expect(readAttachmentTransfer(root, manifest.id)).resolves.toMatchObject({
      companyId: "company-a", issueId: "issue-a", agentId: "agent-a", runId: "run-a",
      totalBytes: 4, contentType: "application/octet-stream", status: "open",
    });
  });
});
