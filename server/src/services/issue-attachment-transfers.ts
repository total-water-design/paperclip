import { createHash, randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { z } from "zod";
import { resolvePaperclipInstanceRoot } from "../home-paths.js";

// One chunk stays below the callback bridge's 256 KiB per-request bound while
// carrying exact binary bytes rather than a base64/JSON envelope.
export const ATTACHMENT_TRANSFER_CHUNK_BYTES = 128 * 1024;
export const ATTACHMENT_TRANSFER_MAX_BYTES = 64 * 1024 * 1024;
export const ATTACHMENT_TRANSFER_MAX_AGE_MS = 24 * 60 * 60 * 1000;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SHA256_RE = /^[0-9a-f]{64}$/;

const attachmentTransferManifestSchema = z.object({
  version: z.literal(1),
  id: z.string().uuid(),
  companyId: z.string().uuid(),
  issueId: z.string().uuid(),
  agentId: z.string().uuid(),
  runId: z.string().uuid(),
  originalFilename: z.string().min(1).max(255).nullable(),
  contentType: z.string().min(1).max(255),
  totalBytes: z.number().int().positive().max(ATTACHMENT_TRANSFER_MAX_BYTES),
  sha256: z.string().regex(SHA256_RE),
  chunkSize: z.number().int().positive().max(ATTACHMENT_TRANSFER_CHUNK_BYTES),
  totalChunks: z.number().int().positive(),
  nextChunk: z.number().int().nonnegative(),
  issueCommentId: z.string().uuid().nullable(),
  createdAt: z.string().datetime(),
  expiresAt: z.string().datetime(),
  status: z.enum(["open", "publishing"]),
}).strict().superRefine((manifest, ctx) => {
  const expectedChunks = Math.ceil(manifest.totalBytes / manifest.chunkSize);
  if (manifest.totalChunks !== expectedChunks) {
    ctx.addIssue({ code: "custom", path: ["totalChunks"], message: "Transfer chunk count is inconsistent" });
  }
  if (manifest.nextChunk > manifest.totalChunks) {
    ctx.addIssue({ code: "custom", path: ["nextChunk"], message: "Transfer progress exceeds its chunk count" });
  }
  if (Date.parse(manifest.expiresAt) <= Date.parse(manifest.createdAt)) {
    ctx.addIssue({ code: "custom", path: ["expiresAt"], message: "Transfer expiry is invalid" });
  }
});

export type AttachmentTransferManifest = z.infer<typeof attachmentTransferManifestSchema>;

export type AssembledAttachmentTransfer = {
  filePath: string;
  byteCount: number;
  sha256: string;
};

export function resolveDefaultAttachmentTransferRoot() {
  return path.resolve(resolvePaperclipInstanceRoot(), "attachment-transfers");
}

function transferDir(root: string, id: string) {
  if (!UUID_RE.test(id)) throw new Error("Invalid attachment transfer id");
  return path.join(root, id);
}

function manifestPath(root: string, id: string) {
  return path.join(transferDir(root, id), "manifest.json");
}

function chunkPath(root: string, id: string, index: number) {
  if (!Number.isSafeInteger(index) || index < 0) throw new Error("Invalid attachment chunk index");
  return path.join(transferDir(root, id), `chunk-${index}`);
}

function assembledPath(root: string, id: string) {
  return path.join(transferDir(root, id), "assembled.bin");
}

function mutationLockPath(root: string, id: string) {
  return path.join(transferDir(root, id), "mutation.lock");
}

async function atomicWrite(target: string, bytes: string | Buffer) {
  await fs.mkdir(path.dirname(target), { recursive: true, mode: 0o700 });
  const temp = `${target}.tmp-${randomUUID()}`;
  await fs.writeFile(temp, bytes, { mode: 0o600 });
  await fs.rename(temp, target);
}

async function withTransferMutationLock<T>(root: string, id: string, operation: () => Promise<T>): Promise<T | null> {
  const lockPath = mutationLockPath(root, id);
  let lock: Awaited<ReturnType<typeof fs.open>>;
  try {
    lock = await fs.open(lockPath, "wx", 0o600);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") return null;
    throw error;
  }
  try {
    return await operation();
  } finally {
    await lock.close().catch(() => undefined);
    await fs.rm(lockPath, { force: true }).catch(() => undefined);
  }
}

export async function createAttachmentTransfer(
  root: string,
  input: Omit<AttachmentTransferManifest, "version" | "id" | "totalChunks" | "nextChunk" | "createdAt" | "expiresAt" | "status">,
  now = new Date(),
) {
  const id = randomUUID();
  const manifest = attachmentTransferManifestSchema.parse({
    version: 1,
    id,
    ...input,
    totalChunks: Math.ceil(input.totalBytes / input.chunkSize),
    nextChunk: 0,
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + ATTACHMENT_TRANSFER_MAX_AGE_MS).toISOString(),
    status: "open",
  });
  await atomicWrite(manifestPath(root, id), JSON.stringify(manifest));
  return manifest;
}

export async function readAttachmentTransfer(root: string, id: string) {
  const raw = await fs.readFile(manifestPath(root, id), "utf8");
  return attachmentTransferManifestSchema.parse(JSON.parse(raw));
}

export function attachmentTransferExpired(manifest: AttachmentTransferManifest, now = new Date()) {
  return Date.parse(manifest.expiresAt) <= now.getTime();
}

export async function removeAttachmentTransfer(root: string, id: string) {
  await fs.rm(transferDir(root, id), { recursive: true, force: true });
}

export async function writeAttachmentTransferChunk(
  root: string,
  manifest: AttachmentTransferManifest,
  index: number,
  bytes: Buffer,
) {
  const updated = await withTransferMutationLock(root, manifest.id, async () => {
    const current = await readAttachmentTransfer(root, manifest.id);
    if (current.status !== "open") throw new Error("Attachment transfer is not open");
    if (index !== current.nextChunk) throw new Error("Attachment chunks must be uploaded in order and cannot be replayed");
    const expected = index === current.totalChunks - 1
      ? current.totalBytes - index * current.chunkSize
      : current.chunkSize;
    if (bytes.length !== expected) throw new Error(`Attachment chunk must contain exactly ${expected} bytes`);
    await atomicWrite(chunkPath(root, current.id, index), bytes);
    const next = attachmentTransferManifestSchema.parse({ ...current, nextChunk: index + 1 });
    await atomicWrite(manifestPath(root, current.id), JSON.stringify(next));
    return next;
  });
  if (!updated) throw new Error("Attachment transfer is busy");
  return updated;
}

export async function claimAttachmentTransfer(root: string, manifest: AttachmentTransferManifest) {
  return await withTransferMutationLock(root, manifest.id, async () => {
    const current = await readAttachmentTransfer(root, manifest.id);
    if (current.status !== "open" || current.nextChunk !== current.totalChunks) return null;
    const claimed = attachmentTransferManifestSchema.parse({ ...current, status: "publishing" });
    await atomicWrite(manifestPath(root, current.id), JSON.stringify(claimed));
    return claimed;
  });
}

export async function assembleAttachmentTransfer(
  root: string,
  manifest: AttachmentTransferManifest,
): Promise<AssembledAttachmentTransfer> {
  const hash = createHash("sha256");
  const target = assembledPath(root, manifest.id);
  const temp = `${target}.tmp-${randomUUID()}`;
  const output = await fs.open(temp, "wx", 0o600);
  let byteCount = 0;
  try {
    for (let index = 0; index < manifest.totalChunks; index += 1) {
      // Only one bounded chunk is resident at once; a 64 MiB artifact is never
      // assembled into a process-memory Buffer.
      const bytes = await fs.readFile(chunkPath(root, manifest.id, index));
      const expected = index === manifest.totalChunks - 1
        ? manifest.totalBytes - index * manifest.chunkSize
        : manifest.chunkSize;
      if (bytes.length !== expected) throw new Error(`Attachment chunk ${index} has an invalid byte count`);
      let offset = 0;
      while (offset < bytes.length) {
        const { bytesWritten } = await output.write(bytes, offset, bytes.length - offset);
        if (bytesWritten <= 0) throw new Error(`Attachment chunk ${index} could not be written completely`);
        offset += bytesWritten;
      }
      hash.update(bytes);
      byteCount += bytes.length;
      if (byteCount > ATTACHMENT_TRANSFER_MAX_BYTES) {
        throw new Error("Attachment transfer exceeds the 64 MiB policy");
      }
    }
    await output.sync();
    await output.close();
    await fs.rename(temp, target);
  } catch (error) {
    await output.close().catch(() => undefined);
    await fs.rm(temp, { force: true }).catch(() => undefined);
    throw error;
  }
  return { filePath: target, byteCount, sha256: hash.digest("hex") };
}

export async function releaseAttachmentTransferClaim(root: string, manifest: AttachmentTransferManifest) {
  const released = await withTransferMutationLock(root, manifest.id, async () => {
    const current = await readAttachmentTransfer(root, manifest.id);
    if (current.status !== "publishing") return current;
    const next = attachmentTransferManifestSchema.parse({ ...current, status: "open" });
    await atomicWrite(manifestPath(root, current.id), JSON.stringify(next));
    await fs.rm(assembledPath(root, current.id), { force: true }).catch(() => undefined);
    return next;
  });
  if (!released) throw new Error("Attachment transfer is busy");
  return released;
}

export async function sweepExpiredAttachmentTransfers(root: string, now = new Date()) {
  let entries: import("node:fs").Dirent[];
  try { entries = await fs.readdir(root, { withFileTypes: true }); } catch { return 0; }
  let swept = 0;
  for (const entry of entries) {
    if (!entry.isDirectory() || !UUID_RE.test(entry.name)) continue;
    try {
      const manifest = await readAttachmentTransfer(root, entry.name);
      if (!attachmentTransferExpired(manifest, now)) continue;
    } catch {
      const stat = await fs.stat(path.join(root, entry.name));
      if (now.getTime() - stat.mtimeMs < ATTACHMENT_TRANSFER_MAX_AGE_MS) continue;
    }
    await removeAttachmentTransfer(root, entry.name);
    swept += 1;
  }
  return swept;
}
