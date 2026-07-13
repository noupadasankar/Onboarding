/**
 * Storage abstraction. Decouples the document pipeline from the physical file
 * backend so that swapping local disk for S3 / Azure Blob / MinIO is a single DI
 * binding change — no service or controller edits. Controllers and application
 * services depend on IStorageService only; they never touch `fs` directly.
 *
 * Files are organised by department and category:
 *   uploads/{department}/{category}/{timestamp}-{safeName}
 * e.g. uploads/hr/policies/1783824126457-employee_handbook.pdf
 * The layout keeps departments physically isolated and leaves room for
 * category-level foldering (see SaveFileInput.category) without a schema change.
 */
export interface SaveFileInput {
  /** Canonical department name (hr | finance | it). Becomes the top folder. */
  department: string;
  /** Optional sub-folder within the department. Defaults to "general". */
  category?: string | null;
  /** User-provided file name; sanitised before hitting disk. */
  originalName: string;
  /** File bytes. */
  buffer: Buffer;
}

export interface SavedFile {
  /** Absolute (or backend-native) path used to retrieve the file later. */
  storagePath: string;
  /** Sanitised, timestamped storage filename (no directory component). */
  filename: string;
}

export interface IStorageService {
  /** Persist a file under its department/category folder, creating dirs as needed. */
  save(input: SaveFileInput): Promise<SavedFile>;
  /** Read a stored file's bytes. Throws if it does not exist. */
  download(storagePath: string): Promise<Buffer>;
  /** Remove a stored file. No-op if already absent. */
  delete(storagePath: string): Promise<void>;
  /** True when a file exists at `storagePath`. */
  exists(storagePath: string): Promise<boolean>;
  /** Move/rename a stored file (e.g. re-foldering on category change). */
  move(fromPath: string, toPath: string): Promise<void>;
}
