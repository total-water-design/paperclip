import { z } from "zod";

export const CONFINED_ARTIFACT_TRANSFER_CHUNK_BYTES = 128 * 1024;
export const CONFINED_ARTIFACT_TRANSFER_MAX_BASE64_CHARS =
  Math.ceil(CONFINED_ARTIFACT_TRANSFER_CHUNK_BYTES / 3) * 4;
export const CONFINED_ARTIFACT_TRANSFER_TTL_MS = 15 * 60 * 1000;

export const beginConfinedArtifactTransferSchema = z.object({
  originalFilename: z.string().min(1).max(255),
  contentType: z.string().min(1).max(255),
  byteSize: z.number().int().positive(),
  sha256: z.string().regex(/^[0-9a-f]{64}$/i),
}).strict();

export const appendConfinedArtifactChunkSchema = z.object({
  index: z.number().int().nonnegative(),
  data: z.string().min(1).max(CONFINED_ARTIFACT_TRANSFER_MAX_BASE64_CHARS),
}).strict();

export type BeginConfinedArtifactTransferRequest = z.infer<
  typeof beginConfinedArtifactTransferSchema
>;
export type AppendConfinedArtifactChunkRequest = z.infer<
  typeof appendConfinedArtifactChunkSchema
>;
