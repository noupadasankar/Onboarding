/**
 * In-process implementation of IIndexingQueue.
 *
 * - Bounded concurrency: never runs more than `concurrency` handlers at once, so
 *   the AI service is not overwhelmed by a burst of uploads.
 * - Retry with exponential backoff on failure, up to `maxAttempts`. The handler
 *   is told when it is on the final attempt so it can persist a terminal FAILED
 *   status only then.
 *
 * Suitable for a single-node deployment. For horizontal scaling, replace with a
 * Redis/BullMQ-backed queue exposing the same interface (DI swap only).
 */
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { Logger } from 'pino';
import {
  type IIndexingQueue,
  type IndexingJob,
  type IndexingJobHandler,
} from './indexing-queue';

interface QueuedItem {
  job: IndexingJob;
  attempt: number;
}

/** Tuning constants — modest defaults appropriate for a single AI service. */
const DEFAULT_CONCURRENCY = 2;
const MAX_ATTEMPTS = 3;
const BASE_BACKOFF_MS = 1000;

@injectable()
export class InMemoryIndexingQueue implements IIndexingQueue {
  private handler: IndexingJobHandler | null = null;
  private readonly waiting: QueuedItem[] = [];
  private active = 0;

  // Tuning is fixed here rather than constructor-injected so Inversify only has
  // to resolve the Logger (undecorated primitive params break DI resolution).
  private readonly concurrency = DEFAULT_CONCURRENCY;
  private readonly maxAttempts = MAX_ATTEMPTS;

  constructor(@inject(TYPES.Logger) private readonly log: Logger) {}

  process(handler: IndexingJobHandler): void {
    this.handler = handler;
  }

  enqueue(job: IndexingJob): void {
    this.waiting.push({ job, attempt: 1 });
    this.pump();
  }

  size(): number {
    return this.active + this.waiting.length;
  }

  /** Start as many jobs as free concurrency slots allow. */
  private pump(): void {
    if (!this.handler) {
      this.log.warn('indexing_queue:no_handler_registered');
      return;
    }
    while (this.active < this.concurrency && this.waiting.length > 0) {
      const item = this.waiting.shift()!;
      this.active += 1;
      void this.run(item);
    }
  }

  private async run(item: QueuedItem): Promise<void> {
    const { job, attempt } = item;
    const isFinalAttempt = attempt >= this.maxAttempts;
    try {
      await this.handler!(job, { attempt, isFinalAttempt });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (!isFinalAttempt) {
        const delay = BASE_BACKOFF_MS * 2 ** (attempt - 1);
        this.log.warn(
          { document_id: job.documentId, attempt, retry_in_ms: delay, error: msg },
          'indexing_queue:retry',
        );
        setTimeout(() => {
          this.waiting.push({ job, attempt: attempt + 1 });
          this.pump();
        }, delay).unref?.();
      } else {
        this.log.error(
          { document_id: job.documentId, attempt, error: msg },
          'indexing_queue:exhausted',
        );
      }
    } finally {
      this.active -= 1;
      this.pump();
    }
  }
}
