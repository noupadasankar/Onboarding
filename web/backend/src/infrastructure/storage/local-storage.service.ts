/**
 * Local-filesystem implementation of IStorageService.
 *
 * Root is `<cwd>/uploads`. Files are written to
 *   uploads/{department}/{category}/{timestamp}-{safeName}
 * Directories are created on demand. To migrate to object storage later, provide
 * an S3StorageService with the same interface and swap the DI binding — nothing
 * else changes.
 */
import { inject, injectable } from 'inversify';
import { join, dirname } from 'node:path';
import { access, mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { TYPES } from '../../core/di/types';
import type { Logger } from 'pino';
import {
  type IStorageService,
  type SaveFileInput,
  type SavedFile,
} from './storage.service';

/** Default sub-folder when a document has no explicit category. */
const DEFAULT_CATEGORY = 'general';

@injectable()
export class LocalStorageService implements IStorageService {
  private readonly root: string;

  constructor(@inject(TYPES.Logger) private readonly log: Logger) {
    this.root = join(process.cwd(), 'uploads');
  }

  /** Collapse anything unexpected to a safe path segment (no separators/traversal). */
  private safeSegment(value: string, fallback: string): string {
    const cleaned = value.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '');
    return cleaned.length > 0 ? cleaned : fallback;
  }

  async save(input: SaveFileInput): Promise<SavedFile> {
    const department = this.safeSegment(input.department, 'general');
    const category = this.safeSegment(input.category ?? DEFAULT_CATEGORY, DEFAULT_CATEGORY);
    const filename = `${Date.now()}-${input.originalName.replace(/[^\w.-]/g, '_')}`;

    const dir = join(this.root, department, category);
    const storagePath = join(dir, filename);

    await mkdir(dir, { recursive: true });
    await writeFile(storagePath, input.buffer);

    this.log.info({ storage_path: storagePath, department, category }, 'storage:saved');
    return { storagePath, filename };
  }

  async download(storagePath: string): Promise<Buffer> {
    return readFile(storagePath);
  }

  async delete(storagePath: string): Promise<void> {
    // force:true → no error if the file is already gone (idempotent).
    await rm(storagePath, { force: true });
    this.log.info({ storage_path: storagePath }, 'storage:deleted');
  }

  async exists(storagePath: string): Promise<boolean> {
    try {
      await access(storagePath);
      return true;
    } catch {
      return false;
    }
  }

  async move(fromPath: string, toPath: string): Promise<void> {
    await mkdir(dirname(toPath), { recursive: true });
    await rename(fromPath, toPath);
    this.log.info({ from: fromPath, to: toPath }, 'storage:moved');
  }
}
