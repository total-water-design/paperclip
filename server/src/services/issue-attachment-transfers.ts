import { createHash, randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { resolvePaperclipInstanceRoot } from "../home-paths.js";

// Base64 plus JSON metadata must remain below the confined bridge's 256 KiB
// request ceiling.
export const ATTACHMENT_TRANSFER_CHUNK_BYTES = 128 * 1024;
export const ATTACHMENT_TRANSFER_MAX_AGE_MS = 24 * 60 * 60 * 1000;

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type AttachmentTransferManifest = {
  version: 1;
  id: string;
  companyId: string;
  issueId: string;
  agentId: string;
  runId: string;
  originalFilename: string | null;
  contentType: string;
  totalBytes: number;
  sha256: string;
  chunkSize: number;
  totalChunks: number;
  nextChunk: number;
  issueCommentId: string | null;
  createdAt: string;
  expiresAt: string;
  status: "open" | "publishing";
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

async function atomicWrite(target: string, bytes: string | Buffer) {
  await fs.mkdir(path.dirname(target), { recursive: true });
  const temp = `${target}.tmp-${randomUUID()}`;
  await fs.writeFile(temp, bytes, { mode: 0o600 });
  await fs.rename(temp, target);
}

export async function createAttachmentTransfer(
  root: string,
  input: Omit<AttachmentTransferManifest, "version" | "id" | "totalChunks" | "nextChunk" | "createdAt" | "expiresAt" | "status">,
  now = new Date(),
) {
  const id = randomUUID();
  const manifest: AttachmentTransferManifest = {
    version: 1,
    id,
    ...input,
    totalChunks: Math.ceil(input.totalBytes / input.chunkSize),
    nextChunk: 0,
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + ATTACHMENT_TRANSFER_MAX_AGE_MS).toISOString(),
    status: "open",
  };
  await atomicWrite(manifestPath(root, id), JSON.stringify(manifest));
  return manifest;
}

export async function readAttachmentTransfer(root: string, id: string) {
  const raw = await fs.readFile(manifestPath(root, id), "utf8");
  return JSON.parse(raw) as AttachmentTransferManifest;
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
  if (manifest.status !== "open") throw new Error("Attachment transfer is not open");
  if (index !== manifest.nextChunk) throw new Error("Attachment chunks must be uploaded in order");
  const expected = index === manifest.totalChunks - 1
    ? manifest.totalBytes - index * manifest.chunkSize
    : manifest.chunkSize;
  if (bytes.length !== expected) throw new Error(`Attachment chunk must contain exactly ${expected} bytes`);
  await atomicWrite(chunkPath(root, manifest.id, index), bytes);
  const updated = { ...manifest, nextChunk: index + 1 };
  await atomicWrite(manifestPath(root, manifest.id), JSON.stringify(updated));
  return updated;
}

export async function claimAttachmentTransfer(root: string, manifest: AttachmentTransferManifest) {
  const lockPath = path.join(transferDir(root, manifest.id), "publish.lock");
  let lock: Awaited<ReturnType<typeof fs.open>>;
  try {
    lock = await fs.open(lockPath, "wx", 0o600);
    await lock.close();
  } catch {
    return null;
  }
  const current = await readAttachmentTransfer(root, manifest.id);
  if (current.status !== "open" || current.nextChunk !== current.totalChunks) {
    await fs.rm(lockPath, { force: true });
    return null;
  }
  const claimed = { ...current, status: "publishing" as const };
  await atomicWrite(manifestPath(root, manifest.id), JSON.stringify(claimed));
  return claimed;
}

export async function assembleAttachmentTransfer(root: string, manifest: AttachmentTransferManifest) {
  const hash = createHash("sha256");
  const chunks: Buffer[] = [];
  let byteCount = 0;
  for (let index = 0; index < manifest.totalChunks; index += 1) {
    const bytes = await fs.readFile(chunkPath(root, manifest.id, index));
    chunks.push(bytes);
    hash.update(bytes);
    byteCount += bytes.length;
  }
  return { bytes: Buffer.concat(chunks), byteCount, sha256: hash.digest("hex") };
}

export async function releaseAttachmentTransferClaim(root: string, manifest: AttachmentTransferManifest) {
  await atomicWrite(manifestPath(root, manifest.id), JSON.stringify({ ...manifest, status: "open" }));
  await fs.rm(path.join(transferDir(root, manifest.id), "publish.lock"), { force: true });
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
