import { createHash, randomUUID, timingSafeEqual } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  CONFINED_ARTIFACT_TRANSFER_CHUNK_BYTES,
  CONFINED_ARTIFACT_TRANSFER_TTL_MS,
} from "@paperclipai/shared";

export const CONFINED_ARTIFACT_TRANSFER_MAX_ACTIVE_PER_RUN = 4;

const SHA256_RE = /^[0-9a-f]{64}$/i;
const STRICT_BASE64_RE = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
const CONTROL_CHARACTER_RE = /[\u0000-\u001f\u007f]/;

export interface ConfinedArtifactTransferBinding {
  companyId: string;
  runId: string;
  agentId: string;
  issueId: string;
}

export interface BeginConfinedArtifactTransferInput extends ConfinedArtifactTransferBinding {
  originalFilename: string;
  contentType: string;
  byteSize: number;
  sha256: string;
}

export interface ConfinedArtifactTransferDescriptor {
  transferId: string;
  chunkBytes: number;
  expiresAt: string;
}

export interface CompletedConfinedArtifactTransfer {
  originalFilename: string;
  contentType: string;
  byteSize: number;
  sha256: string;
  body: Buffer;
}

interface TransferState extends BeginConfinedArtifactTransferInput {
  id: string;
  filePath: string;
  createdAtMs: number;
  expiresAtMs: number;
  receivedBytes: number;
  nextIndex: number;
  hash: ReturnType<typeof createHash>;
}

export class ConfinedArtifactTransferError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export interface ConfinedArtifactTransferStoreOptions {
  maxBytes: number;
  rootDir?: string;
  chunkBytes?: number;
  ttlMs?: number;
  maxActivePerRun?: number;
  now?: () => number;
}

/**
 * Process-local transfer ledger backed by mode-0600 spool files.
 *
 * Every mutation rechecks the complete company/run/agent/issue binding. The
 * client-supplied filename is metadata only and never participates in a spool
 * path. A transfer is usable only while its in-memory ledger entry exists; an
 * abandoned file after a process crash is therefore not addressable and the
 * operating system's temporary-directory lifecycle removes it.
 */
export class ConfinedArtifactTransferStore {
  readonly maxBytes: number;
  readonly chunkBytes: number;
  readonly ttlMs: number;

  private readonly maxActivePerRun: number;
  private readonly rootDir: string;
  private readonly now: () => number;
  private readonly transfers = new Map<string, TransferState>();
  private readonly locked = new Set<string>();
  private cleanupTimer: NodeJS.Timeout | null = null;

  constructor(options: ConfinedArtifactTransferStoreOptions) {
    if (!Number.isSafeInteger(options.maxBytes) || options.maxBytes < 1) {
      throw new Error("maxBytes must be a positive safe integer");
    }
    this.maxBytes = options.maxBytes;
    this.chunkBytes = options.chunkBytes ?? CONFINED_ARTIFACT_TRANSFER_CHUNK_BYTES;
    this.ttlMs = options.ttlMs ?? CONFINED_ARTIFACT_TRANSFER_TTL_MS;
    this.maxActivePerRun =
      options.maxActivePerRun ?? CONFINED_ARTIFACT_TRANSFER_MAX_ACTIVE_PER_RUN;
    this.rootDir =
      options.rootDir ??
      path.join(os.tmpdir(), `paperclip-confined-artifacts-${process.pid}-${randomUUID()}`);
    this.now = options.now ?? Date.now;

    if (!Number.isSafeInteger(this.chunkBytes) || this.chunkBytes < 1) {
      throw new Error("chunkBytes must be a positive safe integer");
    }
    if (!Number.isSafeInteger(this.ttlMs) || this.ttlMs < 1) {
      throw new Error("ttlMs must be a positive safe integer");
    }
    if (!Number.isSafeInteger(this.maxActivePerRun) || this.maxActivePerRun < 1) {
      throw new Error("maxActivePerRun must be a positive safe integer");
    }
  }

  async begin(input: BeginConfinedArtifactTransferInput): Promise<ConfinedArtifactTransferDescriptor> {
    await this.sweepExpired();
    validateSafeFilename(input.originalFilename);
    validateContentType(input.contentType);
    if (!Number.isSafeInteger(input.byteSize) || input.byteSize < 1) {
      throw new ConfinedArtifactTransferError(422, "invalid_byte_size", "Artifact byteSize must be a positive integer");
    }
    if (input.byteSize > this.maxBytes) {
      throw new ConfinedArtifactTransferError(422, "attachment_too_large", "Artifact exceeds the attachment size limit");
    }
    if (!SHA256_RE.test(input.sha256)) {
      throw new ConfinedArtifactTransferError(422, "invalid_sha256", "Artifact sha256 must be 64 hexadecimal characters");
    }

    const activeForRun = [...this.transfers.values()].filter(
      (transfer) =>
        transfer.companyId === input.companyId &&
        transfer.runId === input.runId &&
        transfer.agentId === input.agentId,
    ).length;
    if (activeForRun >= this.maxActivePerRun) {
      throw new ConfinedArtifactTransferError(429, "too_many_transfers", "Too many active artifact transfers for this run");
    }

    await fs.mkdir(this.rootDir, { recursive: true, mode: 0o700 });
    const id = randomUUID();
    const filePath = path.join(this.rootDir, `${id}.part`);
    const handle = await fs.open(filePath, "wx", 0o600);
    await handle.close();

    const createdAtMs = this.now();
    const state: TransferState = {
      ...input,
      sha256: input.sha256.toLowerCase(),
      id,
      filePath,
      createdAtMs,
      expiresAtMs: createdAtMs + this.ttlMs,
      receivedBytes: 0,
      nextIndex: 0,
      hash: createHash("sha256"),
    };
    this.transfers.set(id, state);
    this.startCleanupTimer();

    return {
      transferId: id,
      chunkBytes: this.chunkBytes,
      expiresAt: new Date(state.expiresAtMs).toISOString(),
    };
  }

  async appendChunk(
    transferId: string,
    binding: ConfinedArtifactTransferBinding,
    input: { index: number; data: string },
  ): Promise<{ nextIndex: number; receivedBytes: number }> {
    return this.withTransfer(transferId, binding, async (transfer) => {
      if (!Number.isSafeInteger(input.index) || input.index < 0 || input.index !== transfer.nextIndex) {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(
          409,
          "chunk_out_of_order",
          `Expected artifact chunk ${transfer.nextIndex}`,
        );
      }

      let bytes: Buffer;
      const maxEncodedBytes = Math.ceil(this.chunkBytes / 3) * 4;
      try {
        if (typeof input.data !== "string" || input.data.length > maxEncodedBytes) {
          throw new Error("Encoded chunk exceeds the limit");
        }
        bytes = decodeStrictBase64(input.data);
      } catch {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(422, "malformed_chunk", "Artifact chunk is not canonical bounded base64");
      }
      const expectedChunkBytes = Math.min(
        this.chunkBytes,
        transfer.byteSize - transfer.receivedBytes,
      );
      if (bytes.length !== expectedChunkBytes) {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(422, "invalid_chunk_size", "Artifact chunk has an invalid byte size");
      }

      try {
        await fs.appendFile(transfer.filePath, bytes);
      } catch (error) {
        await this.destroy(transfer);
        throw error;
      }
      transfer.hash.update(bytes);
      transfer.receivedBytes += bytes.length;
      transfer.nextIndex += 1;
      return {
        nextIndex: transfer.nextIndex,
        receivedBytes: transfer.receivedBytes,
      };
    });
  }

  async complete(
    transferId: string,
    binding: ConfinedArtifactTransferBinding,
  ): Promise<CompletedConfinedArtifactTransfer> {
    return this.withTransfer(transferId, binding, async (transfer) => {
      if (transfer.receivedBytes !== transfer.byteSize) {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(409, "incomplete_transfer", "Artifact transfer is incomplete");
      }

      const actualSha256 = transfer.hash.digest();
      const expectedSha256 = Buffer.from(transfer.sha256, "hex");
      if (
        actualSha256.length !== expectedSha256.length ||
        !timingSafeEqual(actualSha256, expectedSha256)
      ) {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(422, "sha256_mismatch", "Artifact sha256 verification failed");
      }

      let body: Buffer;
      try {
        body = await fs.readFile(transfer.filePath);
      } catch (error) {
        await this.destroy(transfer);
        throw error;
      }
      if (body.length !== transfer.byteSize) {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(422, "byte_size_mismatch", "Artifact spool byte size changed");
      }
      const bodySha256 = createHash("sha256").update(body).digest();
      if (!timingSafeEqual(bodySha256, expectedSha256)) {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(422, "sha256_mismatch", "Artifact spool failed sha256 verification");
      }

      const completed: CompletedConfinedArtifactTransfer = {
        originalFilename: transfer.originalFilename,
        contentType: transfer.contentType,
        byteSize: transfer.byteSize,
        sha256: transfer.sha256,
        body,
      };
      await this.destroy(transfer);
      return completed;
    });
  }

  async abort(transferId: string, binding: ConfinedArtifactTransferBinding): Promise<void> {
    await this.withTransfer(transferId, binding, async (transfer) => {
      await this.destroy(transfer);
    });
  }

  async sweepExpired(): Promise<number> {
    const nowMs = this.now();
    const expired = [...this.transfers.values()].filter(
      (transfer) => transfer.expiresAtMs <= nowMs && !this.locked.has(transfer.id),
    );
    await Promise.all(expired.map((transfer) => this.destroy(transfer)));
    return expired.length;
  }

  async close(): Promise<void> {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    this.transfers.clear();
    this.locked.clear();
    await fs.rm(this.rootDir, { recursive: true, force: true });
  }

  private async withTransfer<T>(
    transferId: string,
    binding: ConfinedArtifactTransferBinding,
    operation: (transfer: TransferState) => Promise<T>,
  ): Promise<T> {
    if (this.locked.has(transferId)) {
      throw new ConfinedArtifactTransferError(409, "transfer_busy", "Artifact transfer is busy");
    }
    this.locked.add(transferId);
    try {
      const transfer = this.transfers.get(transferId);
      if (!transfer || !sameBinding(transfer, binding)) {
        throw new ConfinedArtifactTransferError(404, "transfer_not_found", "Artifact transfer not found");
      }
      if (transfer.expiresAtMs <= this.now()) {
        await this.destroy(transfer);
        throw new ConfinedArtifactTransferError(410, "transfer_expired", "Artifact transfer expired");
      }
      await this.sweepExpired();
      return await operation(transfer);
    } finally {
      this.locked.delete(transferId);
    }
  }

  private async destroy(transfer: TransferState): Promise<void> {
    this.transfers.delete(transfer.id);
    await fs.rm(transfer.filePath, { force: true });
  }

  private startCleanupTimer() {
    if (this.cleanupTimer) return;
    const intervalMs = Math.max(1_000, Math.min(this.ttlMs, 60_000));
    this.cleanupTimer = setInterval(() => {
      void this.sweepExpired().catch(() => undefined);
    }, intervalMs);
    this.cleanupTimer.unref();
  }
}

function sameBinding(
  transfer: TransferState,
  binding: ConfinedArtifactTransferBinding,
): boolean {
  return (
    transfer.companyId === binding.companyId &&
    transfer.runId === binding.runId &&
    transfer.agentId === binding.agentId &&
    transfer.issueId === binding.issueId
  );
}

function decodeStrictBase64(value: unknown): Buffer {
  if (typeof value !== "string" || value.length === 0 || !STRICT_BASE64_RE.test(value)) {
    throw new Error("Invalid base64");
  }
  const decoded = Buffer.from(value, "base64");
  if (decoded.toString("base64") !== value) {
    throw new Error("Non-canonical base64");
  }
  return decoded;
}

function validateSafeFilename(value: string): void {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    value !== value.trim() ||
    value === "." ||
    value === ".." ||
    value.includes("/") ||
    value.includes("\\") ||
    CONTROL_CHARACTER_RE.test(value) ||
    Buffer.byteLength(value, "utf8") > 255
  ) {
    throw new ConfinedArtifactTransferError(422, "unsafe_filename", "Artifact filename is unsafe");
  }
}

function validateContentType(value: string): void {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    value.length > 255 ||
    value.includes("\r") ||
    value.includes("\n") ||
    !/^[a-z0-9!#$&^_.+-]+\/[a-z0-9!#$&^_.+-]+(?:\s*;\s*[a-z0-9!#$&^_.+-]+=(?:"[^"\r\n]*"|[a-z0-9!#$&^_.+-]+))*$/i.test(value)
  ) {
    throw new ConfinedArtifactTransferError(422, "invalid_content_type", "Artifact contentType is invalid");
  }
}
