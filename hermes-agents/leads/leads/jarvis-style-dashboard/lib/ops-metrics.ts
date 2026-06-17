import "server-only";
import { runContentScheduler } from "@/lib/content-scheduler";
import {
  getLatestWorkerRunSnapshots,
  getWorkerRunSummary,
  type WorkerRunSummary,
} from "@/lib/worker-run-log";

export interface OpsMetricsPayload {
  generatedAt: string;
  content: {
    dailyTarget: number;
    publishedToday: number;
    approvedToday: number;
    approvedQueued: number;
    pendingBefore: number;
    pendingAfter: number;
    generated: number;
    remainingShortfall: number;
  };
  workers: {
    snapshots: Array<{ worker: string; status: string; ts: string }>;
    summary24h: WorkerRunSummary[];
  };
}

export async function buildOpsMetricsPayload(): Promise<OpsMetricsPayload> {
  const workerNames = [
    "content_scheduler",
    "content_publisher",
    "hunt_protocol",
    "social_growth",
    "sla_follow_up",
  ];
  const [contentPreview, snapshots, summary24h] = await Promise.all([
    runContentScheduler({ dryRun: true }),
    getLatestWorkerRunSnapshots(workerNames),
    getWorkerRunSummary(workerNames, 24),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    content: {
      dailyTarget: contentPreview.dailyTarget,
      publishedToday: contentPreview.publishedToday,
      approvedToday: contentPreview.approvedToday,
      approvedQueued: contentPreview.approvedQueued,
      pendingBefore: contentPreview.pendingBefore,
      pendingAfter: contentPreview.pendingAfter,
      generated: contentPreview.generated,
      remainingShortfall: contentPreview.remainingShortfall,
    },
    workers: {
      snapshots: snapshots.map((s) => ({ worker: s.worker, status: s.status, ts: s.ts })),
      summary24h,
    },
  };
}
