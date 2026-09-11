import type { StorageProvider as StorageProviderId } from "@paperclipai/shared";
import type { Readable } from "node:stream";

export interface PutObjectInput {
  objectKey: string;
  // Readable bodies stream straight to the backend (contentLength must be the
  // exact byte size); Buffer stays supported for small payloads.
  body: Buffer | Readable;
  contentType: string;
  contentLength: number;
}

export interface GetObjectInput {
  objectKey: string;
  range?: {
    start: number;
    end: number;
  };
}

export interface GetObjectResult {
  stream: Readable;
  contentType?: string;
  contentLength?: number;
  etag?: string;
  lastModified?: Date;
}

export interface HeadObjectResult {
  exists: boolean;
  contentType?: string;
  contentLength?: number;
  etag?: string;
  lastModified?: Date;
}

export interface StorageProvider {
  id: StorageProviderId;
  putObject(input: PutObjectInput): Promise<void>;
  getObject(input: GetObjectInput): Promise<GetObjectResult>;
  headObject(input: GetObjectInput): Promise<HeadObjectResult>;
  deleteObject(input: GetObjectInput): Promise<void>;
}

export interface PutFileInput {
  companyId: string;
  namespace: string;
  originalFilename: string | null;
  contentType: string;
  body: Buffer;
}

export interface PutVerifiedFileInput {
  companyId: string;
  namespace: string;
  originalFilename: string | null;
  contentType: string;
  body: Readable;
  byteSize: number;
  sha256: string;
}

export interface PutFileResult {
  provider: StorageProviderId;
  objectKey: string;
  contentType: string;
  byteSize: number;
  sha256: string;
  originalFilename: string | null;
}

export interface StorageService {
  provider: StorageProviderId;
  putFile(input: PutFileInput): Promise<PutFileResult>;
  /**
   * Store a bounded stream whose exact byte count and SHA-256 were already
   * verified before publication. Production storage services always provide
   * this method; it is optional only so older test/plugin mocks remain source
   * compatible.
   */
  putVerifiedFile?(input: PutVerifiedFileInput): Promise<PutFileResult>;
  getObject(companyId: string, objectKey: string, options?: Pick<GetObjectInput, "range">): Promise<GetObjectResult>;
  headObject(companyId: string, objectKey: string): Promise<HeadObjectResult>;
  deleteObject(companyId: string, objectKey: string): Promise<void>;
}
