import "server-only";
import { getSupabaseServer } from "@/lib/supabase-server";
import { getWorkflowStats } from "@/lib/workflow-stats";

export interface HuntAdaptivePolicy {
  minScore: number;
  dailyTarget: number;
  channelCaps: { instagram: number; email: number; sms: number };
  rationale: string[];
}

export interface SocialAdaptivePolicy {
  dailyActionTarget: number;
  maxActionsPerRun: number;
  greetingCapPerRun: number;
  staggerWindowMs: { min: number; max: number };
  rationale: string[];
}

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

export async function buildHuntAdaptivePolicy(): Promise<HuntAdaptivePolicy> {
  const policy: HuntAdaptivePolicy = {
    minScore: 55,
    dailyTarget: 12,
    channelCaps: { instagram: 6, email: 4, sms: 3 },
    rationale: [],
  };

  const workflow = await getWorkflowStats().catch(() => null);
  const supabase = getSupabaseServer();
  if (!supabase || !workflow) {
    policy.rationale.push("fallback defaults (missing supabase/workflow)");
    return policy;
  }

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const { data } = await supabase
    .from("worker_run_logs")
    .select("metadata,status,started_at")
    .eq("worker_name", "hunt_protocol")
    .gte("started_at", sevenDaysAgo)
    .order("started_at", { ascending: false })
    .limit(200);

  let contacted = 0;
  let scored = 0;
  let ig = 0;
  let email = 0;
  let sms = 0;
  let failedRuns = 0;
  for (const row of (data || []) as any[]) {
    const md = (row?.metadata || {}) as Record<string, unknown>;
    contacted += Number(md.contacted || 0);
    scored += Number(md.scored || 0);
    const breakdown = (md.channelBreakdown || {}) as Record<string, unknown>;
    ig += Number(breakdown.instagram || 0);
    email += Number(breakdown.email || 0);
    sms += Number(breakdown.sms || 0);
    if (String(row?.status || "") === "failed") failedRuns += 1;
  }

  const booked = workflow.totals.booked + workflow.totals.completed;
  const contactedToBooked = booked / Math.max(contacted, 1);
  const qualificationRate = contacted / Math.max(scored, 1);

  if (contactedToBooked < 0.2) {
    policy.minScore = clamp(policy.minScore + 6, 45, 75);
    policy.rationale.push("low conversion signal -> raise score threshold");
  } else if (contactedToBooked > 0.5) {
    policy.minScore = clamp(policy.minScore - 4, 45, 75);
    policy.rationale.push("strong conversion signal -> widen top-of-funnel");
  }

  if (qualificationRate < 0.18) {
    policy.dailyTarget = clamp(policy.dailyTarget - 2, 6, 20);
    policy.rationale.push("low qualification -> reduce daily target");
  } else if (qualificationRate > 0.45) {
    policy.dailyTarget = clamp(policy.dailyTarget + 2, 6, 20);
    policy.rationale.push("high qualification -> expand daily target");
  }

  if (failedRuns >= 3) {
    policy.dailyTarget = clamp(policy.dailyTarget - 2, 6, 20);
    policy.rationale.push("recent worker instability -> temporary throttle");
  }

  const totalByChannel = ig + email + sms;
  if (totalByChannel > 0) {
    const igShare = ig / totalByChannel;
    const emailShare = email / totalByChannel;
    const smsShare = sms / totalByChannel;
    policy.channelCaps.instagram = clamp(Math.round(4 + igShare * 6), 3, 8);
    policy.channelCaps.email = clamp(Math.round(2 + emailShare * 5), 2, 6);
    policy.channelCaps.sms = clamp(Math.round(1 + smsShare * 4), 1, 4);
    policy.rationale.push("channel caps rebalanced from 7-day channel mix");
  }

  if (policy.rationale.length === 0) {
    policy.rationale.push("stable metrics -> keep baseline policy");
  }
  return policy;
}

export async function buildSocialAdaptivePolicy(): Promise<SocialAdaptivePolicy> {
  const policy: SocialAdaptivePolicy = {
    dailyActionTarget: 20,
    maxActionsPerRun: 6,
    greetingCapPerRun: 6,
    staggerWindowMs: { min: 6000, max: 26000 },
    rationale: [],
  };

  const supabase = getSupabaseServer();
  if (!supabase) {
    policy.rationale.push("fallback defaults (missing supabase)");
    return policy;
  }

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const { data } = await supabase
    .from("worker_run_logs")
    .select("metadata,status,started_at")
    .eq("worker_name", "social_growth")
    .gte("started_at", sevenDaysAgo)
    .order("started_at", { ascending: false })
    .limit(240);

  let actions = 0;
  let skipped = 0;
  let greetings = 0;
  let failedRuns = 0;
  for (const row of (data || []) as any[]) {
    const md = (row?.metadata || {}) as Record<string, unknown>;
    actions += Number(md.actionsPerformed || 0);
    skipped += Number(md.skippedCount || 0);
    greetings += Number(md.greetingsSent || 0);
    if (String(row?.status || "") === "failed") failedRuns += 1;
  }

  const executionRate = actions / Math.max(actions + skipped, 1);
  const greetingRatio = greetings / Math.max(actions, 1);

  if (executionRate < 0.35) {
    policy.maxActionsPerRun = 4;
    policy.dailyActionTarget = 14;
    policy.staggerWindowMs = { min: 10000, max: 38000 };
    policy.rationale.push("low social execution rate -> stronger throttling");
  } else if (executionRate > 0.7) {
    policy.maxActionsPerRun = 8;
    policy.dailyActionTarget = 24;
    policy.staggerWindowMs = { min: 5000, max: 22000 };
    policy.rationale.push("healthy social execution rate -> allow higher throughput");
  }

  if (greetingRatio > 0.7) {
    policy.greetingCapPerRun = 5;
    policy.rationale.push("greeting-heavy mix -> rebalance toward engagement actions");
  } else if (greetingRatio < 0.25) {
    policy.greetingCapPerRun = 8;
    policy.rationale.push("low greeting mix -> increase welcome outreach");
  }

  if (failedRuns >= 3) {
    policy.maxActionsPerRun = clamp(policy.maxActionsPerRun - 2, 3, 10);
    policy.staggerWindowMs = { min: 12000, max: 45000 };
    policy.rationale.push("worker failures detected -> defensive pacing");
  }

  if (policy.rationale.length === 0) {
    policy.rationale.push("stable social metrics -> keep baseline policy");
  }
  return policy;
}
