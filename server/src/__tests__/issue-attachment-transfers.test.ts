import { createHash } from "node:crypto";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  ATTACHMENT_TRANSFER_CHUNK_BYTES,
  ATTACHMENT_TRANSFER_MAX_BYTES,
  assembleAttachmentTransfer,
  attachmentTransferExpired,
  claimAttachmentTransfer,
  createAttachmentTransfer,
  readAttachmentTransfer,
  sweepExpiredAttachmentTransfers,
  writeAttachmentTransferChunk,
} from "../services/issue-attachment-transfers.js";

const sha256 = (bytes: Buffer) => createHash("sha256").update(bytes).digest("hex");
const COMPANY_ID = "11111111-1111-4111-8111-111111111111";
const ISSUE_ID = "22222222-2222-4222-8222-222222222222";
const AGENT_ID = "33333333-3333-4333-8333-333333333333";
const RUN_ID = "44444444-4444-4444-8444-444444444444";

async function fixture(bytes: Buffer, chunkSize = 4, now = new Date("2026-01-01T00:00:00Z")) {
  const root = await mkdtemp(path.join(tmpdir(), "attachment-transfer-"));
  const manifest = await createAttachmentTransfer(root, {
    companyId: COMPANY_ID,
    issueId: ISSUE_ID,
    agentId: AGENT_ID,
    runId: RUN_ID,
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
    const first = await writeAttachmentTransferChunk(root, manifest, 0, bytes.subarray(0, 4));
    await expect(writeAttachmentTransferChunk(root, first, 0, bytes.subarray(0, 4))).rejects.toThrow("cannot be replayed");
  });

  it("enforces the 64 MiB attachment boundary before accepting any chunks", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "attachment-transfer-cap-"));
    const input = {
      companyId: COMPANY_ID,
      issueId: ISSUE_ID,
      agentId: AGENT_ID,
      runId: RUN_ID,
      originalFilename: "cap.bin",
      contentType: "application/octet-stream",
      sha256: "a".repeat(64),
      chunkSize: ATTACHMENT_TRANSFER_CHUNK_BYTES,
      issueCommentId: null,
    };
    await expect(createAttachmentTransfer(root, { ...input, totalBytes: ATTACHMENT_TRANSFER_MAX_BYTES })).resolves.toMatchObject({
      totalBytes: ATTACHMENT_TRANSFER_MAX_BYTES,
    });
    await expect(createAttachmentTransfer(root, { ...input, totalBytes: ATTACHMENT_TRANSFER_MAX_BYTES + 1 })).rejects.toThrow();
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
    expect(await readFile(assembled.filePath)).toEqual(bytes);
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
      companyId: COMPANY_ID, issueId: ISSUE_ID, agentId: AGENT_ID, runId: RUN_ID,
      totalBytes: 4, contentType: "application/octet-stream", status: "open",
    });
  });
});
