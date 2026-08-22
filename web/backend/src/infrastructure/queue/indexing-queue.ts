/**
 * Document indexing queue.
 *
 * Upload no longer calls the AI service inline ("fire-and-forget"). Instead it
 * enqueues a job and returns immediately; a worker drains the queue with bounded
 * concurrency and retry-with-backoff. This gives the AI service backpressure
 * (never more than N concurrent index calls) and makes transient failures
 * self-healing.
 *
 * The interface is deliberately transport-agnostic: the in-memory implementation
 * here can be swapped for a Redis/BullMQ-backed one (Redis is already in the
 * stack) without touching DocumentService — same enqueue/process contract.
 */
export interface IndexingJob {
  documentId: string;
  uploadedById: string;
  uploadedByRole: string;
}

export interface JobAttempt {
  /** 1-based attempt counter. */
  attempt: number;
  /** True on the last attempt — the handler should mark the doc FAILED here. */
  isFinalAttempt: boolean;
}

export type IndexingJobHandler = (job: IndexingJob, ctx: JobAttempt) => Promise<void>;

export interface IIndexingQueue {
  /** Register the worker that processes each job. Call once at startup. */
  process(handler: IndexingJobHandler): void;
  /** Add a job to the queue. Returns immediately; processing is async. */
  enqueue(job: IndexingJob): Promise<void>;
  /** Number of jobs currently running + waiting (for health/metrics). */
  size(): Promise<number>;
  /** Graceful shutdown — wait for active jobs, close connections. */
  shutdown(): Promise<void>;
}
