/**
 * Redis/BullMQ-backed implementation of IIndexingQueue.
 *
 * - Survives process restarts
 * - Horizontal scaling: multiple backend instances share the same queue
 * - Job persistence, delayed retries, priority support
 * - Metrics via BullMQ's built-in event hooks
 */
import { Queue, Worker, Job } from 'bullmq';
import { inject, injectable } from 'inversify';
import { TYPES } from '../../core/di/types';
import type { Logger } from 'pino';
import type { RedisService } from '../cache/redis.service';
import {
  type IIndexingQueue,
  type IndexingJob,
  type IndexingJobHandler,
} from './indexing-queue';

const QUEUE_NAME = 'document-indexing';
const DEFAULT_CONCURRENCY = 2;
const MAX_ATTEMPTS = 3;
const BASE_BACKOFF_MS = 1000;

interface JobData extends IndexingJob {}

@injectable()
export class BullMQIndexingQueue implements IIndexingQueue {
  private queue: Queue<JobData>;
  private worker: Worker<JobData> | null = null;
  private handler: IndexingJobHandler | null = null;
  private readonly concurrency: number;

  constructor(
    @inject(TYPES.Logger) private readonly log: Logger,
    @inject(TYPES.RedisService) private readonly redisService: RedisService,
  ) {
    this.concurrency = DEFAULT_CONCURRENCY;

    this.queue = new Queue<JobData>(QUEUE_NAME, {
      connection: this.redisService.client,
      defaultJobOptions: {
        attempts: MAX_ATTEMPTS,
        backoff: {
          type: 'exponential',
          delay: BASE_BACKOFF_MS,
        },
        removeOnComplete: { age: 3600, count: 1000 },
        removeOnFail: { age: 86400, count: 5000 },
      },
    });

    this.queue.on('error', (err) => {
      this.log.error({ err }, 'indexing_queue:redis_error');
    });
  }

  process(handler: IndexingJobHandler): void {
    this.handler = handler;

    this.worker = new Worker<JobData>(
      QUEUE_NAME,
      async (job: Job<JobData>) => {
        if (!this.handler) {
          throw new Error('No handler registered for indexing queue');
        }
        const attempt = job.attemptsMade + 1;
        const isFinalAttempt = attempt >= MAX_ATTEMPTS;
        await this.handler(job.data, { attempt, isFinalAttempt });
      },
      {
        connection: this.redisService.client,
        concurrency: this.concurrency,
        lockDuration: 30000,
      },
    );

    this.worker.on('completed', (job) => {
      this.log.info({ document_id: job.data.documentId, attempt: job.attemptsMade + 1 }, 'indexing_queue:job_completed');
    });

    this.worker.on('failed', (job, err) => {
      this.log.error(
        { document_id: job?.data?.documentId, attempt: job?.attemptsMade ?? 0, error: err?.message },
        'indexing_queue:job_failed',
      );
    });

    this.worker.on('error', (err) => {
      this.log.error({ err }, 'indexing_queue:worker_error');
    });
  }

  async enqueue(job: IndexingJob): Promise<void> {
    await this.queue.add('index-document', job);
    this.log.info({ document_id: job.documentId }, 'indexing_queue:job_enqueued');
  }

  async size(): Promise<number> {
    const [waiting, active, delayed] = await Promise.all([
      this.queue.getWaitingCount(),
      this.queue.getActiveCount(),
      this.queue.getDelayedCount(),
    ]);
    return waiting + active + delayed;
  }

  async shutdown(): Promise<void> {
    this.log.info('indexing_queue:shutting_down');
    if (this.worker) {
      await this.worker.close();
      this.worker = null;
    }
    await this.queue.close();
    this.log.info('indexing_queue:shutdown_complete');
  }
}
