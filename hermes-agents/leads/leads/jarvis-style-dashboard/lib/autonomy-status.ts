import "server-only";
import { getWorkflowStats } from "@/lib/workflow-stats";
import { getSupabaseServer } from "@/lib/supabase-server";
import { runContentScheduler } from "@/lib/content-scheduler";
import { getLatestWorkerRunSnapshots, getWorkerRunSummary } from "@/lib/worker-run-log";

export interface AutonomyStatusSnapshot {
  generatedAt: string;
  overallProgressPercent: number;
  pillars: Array<{
    key: string;
    label: string;
    progressPercent: number;
    status: "done" | "in_progress" | "next";
    note: string;
  }>;
  doneNow: string[];
  inProgressNow: string[];
  nextActions: string[];
}

function clamp(n: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, n));
}

function computeWorkerHealth(
  summary: { completed: number; failed: number; started: number; duplicate: number } | undefined,
  fallback: number,
): number {
  if (!summary) return fallback;
  const totalRuns = summary.completed + summary.failed + summary.started;
  if (totalRuns <= 0) return fallback;
  const completionRate = Math.round((summary.completed / totalRuns) * 100);
  const failPenalty = summary.failed * 8;
  const duplicatePenalty = summary.duplicate * 3;
  const startedPenalty = summary.started * 2;
  return clamp(completionRate - failPenalty - duplicatePenalty - startedPenalty, 25, 98);
}

export async function buildAutonomyStatusSnapshot(): Promise<AutonomyStatusSnapshot> {
  const workflow = await getWorkflowStats().catch(() => null);
  const supabase = getSupabaseServer();
  const schedulerPreview = await runContentScheduler({ dryRun: true }).catch(() => null);
  const runSnapshots = await getLatestWorkerRunSnapshots([
    "content_scheduler",
    "content_publisher",
    "hunt_protocol",
    "social_growth",
    "sla_follow_up",
  ]).catch(() => []);
  const runSummary24h = await getWorkerRunSummary(
    ["content_scheduler", "content_publisher", "hunt_protocol", "social_growth", "sla_follow_up"],
    24,
  ).catch(() => []);
  const summaryByWorker = new Map(runSummary24h.map((row) => [row.worker, row]));

  let contentPending = 0;
  let contentApproved = 0;
  let contentPublished = 0;
  if (supabase) {
    const [{ count: pending }, { count: approved }, { count: published }] = await Promise.all([
      supabase
        .from("content_vault")
        .select("*", { count: "exact", head: true })
        .eq("status", "pending_review"),
      supabase
        .from("content_vault")
        .select("*", { count: "exact", head: true })
        .eq("status", "approved"),
      supabase
        .from("content_vault")
        .select("*", { count: "exact", head: true })
        .eq("status", "published"),
    ]);
    contentPending = pending || 0;
    contentApproved = approved || 0;
    contentPublished = published || 0;
  }

  const leads = workflow?.totals.leads || 0;
  const pending = workflow?.totals.pending || 0;
  const awaitingDeposit = workflow?.totals.awaitingDeposit || 0;
  const booked = workflow?.totals.booked || 0;
  const completed = workflow?.totals.completed || 0;

  const leadPipelineHealth =
    leads > 0
      ? clamp(Math.round(((awaitingDeposit + booked + completed) / Math.max(leads, 1)) * 100))
      : 35;

  const closingHealth =
    leads > 0 ? clamp(Math.round(((booked + completed) / Math.max(leads, 1)) * 100)) : 30;

  const contentHealth = clamp(
    Math.round((Math.min(contentPublished, 20) / 20) * 100) +
      (contentApproved > 0 ? 10 : 0) +
      (contentPending > 0 ? 8 : 0),
  );

  const memoryHealth = 80;
  const snapshotMap = new Map(runSnapshots.map((s) => [s.worker, s]));
  const schedulerRun = snapshotMap.get("content_scheduler");
  const publisherRun = snapshotMap.get("content_publisher");
  const huntRun = snapshotMap.get("hunt_protocol");
  const socialRun = snapshotMap.get("social_growth");
  const slaRun = snapshotMap.get("sla_follow_up");
  const huntHealth = computeWorkerHealth(summaryByWorker.get("hunt_protocol"), 48);
  const socialHealth = computeWorkerHealth(summaryByWorker.get("social_growth"), 45);
  const slaHealth = computeWorkerHealth(summaryByWorker.get("sla_follow_up"), 62);

  const pillars = [
    {
      key: "memory",
      label: "Memory + Context Continuity",
      progressPercent: memoryHealth,
      status: "in_progress" as const,
      note: "Persistent memory, recall context, and summarizer loop are in place.",
    },
    {
      key: "lead_pipeline",
      label: "Lead/Deposit/Consent/Booking Pipeline",
      progressPercent: Math.max(leadPipelineHealth, closingHealth),
      status: "in_progress" as const,
      note: `Leads=${leads}, pending=${pending}, awaiting deposit=${awaitingDeposit}, booked=${booked}, completed=${completed}.`,
    },
    {
      key: "content",
      label: "Content Engine (20 posts/day target)",
      progressPercent: contentHealth,
      status: "in_progress" as const,
      note: `Published=${contentPublished}, approved queue=${contentApproved}, pending review=${contentPending}; scheduler shortfall=${
        schedulerPreview?.remainingShortfall ?? "n/a"
      }; scheduler=${schedulerRun?.status || "unknown"}, publisher=${publisherRun?.status || "unknown"}.`,
    },
    {
      key: "hunt_protocol",
      label: "Hunt Protocol + New Client Acquisition Loop",
      progressPercent: huntHealth,
      status: "in_progress" as const,
      note: `Autonomous hunt cron is active with outreach routing + dedupe cooldown; last run=${
        huntRun?.status || "unknown"
      }. Lead scoring + stop conditions are live; threshold/cap tuning remains.`,
    },
    {
      key: "social_growth",
      label: "Social Growth Loop (engage, greet, follow, comment)",
      progressPercent: socialHealth,
      status: "in_progress" as const,
      note: `Daily staggered social actions with history-aware greetings are active; last run=${
        socialRun?.status || "unknown"
      }. Radius/learning signal tuning remains.`,
    },
    {
      key: "sla_follow_up",
      label: "SLA Follow-Up Loop",
      progressPercent: slaHealth,
      status: "in_progress" as const,
      note: `Hourly SLA worker active with 24h dedupe; last run=${slaRun?.status || "unknown"}.`,
    },
  ];

  const overallProgressPercent = clamp(
    Math.round(
      pillars.reduce((sum, p) => sum + p.progressPercent, 0) / pillars.length,
    ),
  );

  return {
    generatedAt: new Date().toISOString(),
    overallProgressPercent,
    pillars,
    doneNow: [
      "Content review queue is live in Content View for Post with real Approve/Deny updates.",
      "Content publisher worker is live to move approved items into published status tracking.",
      "Memory continuity stack is active (conversation memory + system memory context + fallback).",
      "Core booking lifecycle paths exist for intake -> approval -> deposit -> booked -> completion.",
      "Autonomous workers are in place for content scheduling, hunt protocol, social growth, and SLA follow-up loops.",
      "Social growth worker can greet new engagers, follow, like, and comment with staggered pacing.",
      "Worker run idempotency + fallback audit layer is wired for autonomous cron safety.",
    ],
    inProgressNow: [
      "Lifecycle hardening with explicit state transition guards and guardrail checks.",
      "Dedupe/idempotency hardening for autonomous outreach and follow-up execution.",
      "Standardized status reporting wired to real workflow/content data.",
    ],
    nextActions: [
      "Tune hunt scoring thresholds and channel caps against conversion quality metrics.",
      "Tune social radius heuristics and action allocation model from reply/deposit outcomes.",
      "Connect publisher execution to external channel posting APIs and persist provider post IDs.",
      "Apply worker/content tracking migrations in all deployment environments and verify with ops metrics.",
    ],
  };
}
