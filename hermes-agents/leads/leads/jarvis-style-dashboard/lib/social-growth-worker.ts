import "server-only";
import { beginWorkerRun, completeWorkerRun, failWorkerRun } from "@/lib/worker-run-log";
import { getSupabaseServer } from "@/lib/supabase-server";
import { runSocialRunner } from "@/lib/social-engagement-runner";

interface LeadHistoryRow {
  id: string;
  name: string | null;
  concept: string | null;
  notes: string | null;
}

interface SocialTarget {
  username: string;
  source: "comment_interest" | "dm_inbound" | "follow_back";
  reason: string;
  historySnippet: string | null;
}

type SocialActionKind = "follow" | "like" | "comment";

export interface SocialGrowthRunResult {
  scannedComments: number;
  classifiedDms: number;
  followSignals: number;
  targetsConsidered: number;
  actionsPlanned: number;
  actionsPerformed: number;
  greetingsSent: number;
  likesPerformed: number;
  commentsPerformed: number;
  followsPerformed: number;
  skipped: Array<{ username: string; reason: string }>;
}

const SOCIAL_DAILY_ACTION_TARGET = 20;
const MAX_ACTIONS_PER_RUN = 6;
const MAX_GREETINGS_PER_RUN = 6;
const WORKER_INTERVAL_MINUTES = 60;
const LOCAL_RADIUS_KEYWORDS = [
  "northridge",
  "los angeles",
  "la",
  "san fernando valley",
  "woodland hills",
  "sherman oaks",
  "encino",
  "van nuys",
  "burbank",
  "pasadena",
  "glendale",
  "santa clarita",
];
const TATTOO_INTENT_KEYWORDS = [
  "tattoo",
  "ink",
  "sleeve",
  "irezumi",
  "black and grey",
  "cover up",
  "coverup",
  "portrait piece",
  "session",
];

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomBetween(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function normalizeUsername(raw: string | undefined): string | null {
  if (!raw) return null;
  const value = raw.replace(/^@/, "").trim().toLowerCase();
  if (!value || value === "unknown") return null;
  return value;
}

function extractHandleFromText(value: string | null): string | null {
  const match = (value || "").match(/@([a-zA-Z0-9._]+)/);
  return match?.[1]?.toLowerCase() || null;
}

function looksLocalTattooSignal(text: string): boolean {
  const lower = text.toLowerCase();
  const hasTattooIntent = TATTOO_INTENT_KEYWORDS.some((k) => lower.includes(k));
  const hasLocalSignal = LOCAL_RADIUS_KEYWORDS.some((k) => lower.includes(k));
  return hasTattooIntent && hasLocalSignal;
}

function buildPhilosophyGreeting(username: string, historySnippet: string | null): string {
  const name = username.split(".")[0] || username;
  if (historySnippet) {
    return `Hey ${name}, appreciate the continued support. I remember our previous exchange and wanted to check in with zero pressure - if you are refining ideas, I am happy to help with direction.`;
  }
  return `Hey ${name}, thanks for engaging with the artwork. If you ever want to share tattoo ideas or references, I am happy to listen and help guide next steps - no rush.`;
}

function buildCommentText(): string {
  const options = [
    "Clean concept and strong direction. Respect.",
    "Love the detail and story in this piece.",
    "Great eye for composition - this is solid work.",
    "Strong vision here. Appreciate you sharing it.",
  ];
  return options[randomBetween(0, options.length - 1)];
}

async function computeActionPreferenceOrder(): Promise<SocialActionKind[]> {
  const supabase = getSupabaseServer();
  if (!supabase) return ["follow", "like", "comment"];
  const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const { data, error } = await supabase
    .from("worker_run_logs")
    .select("metadata,started_at")
    .eq("worker_name", "social_growth")
    .gte("started_at", since)
    .order("started_at", { ascending: false })
    .limit(300);
  if (error || !data) return ["follow", "like", "comment"];

  let follows = 0;
  let likes = 0;
  let comments = 0;
  let totalActions = 0;
  for (const row of data as any[]) {
    follows += Number(row?.metadata?.followsPerformed || 0);
    likes += Number(row?.metadata?.likesPerformed || 0);
    comments += Number(row?.metadata?.commentsPerformed || 0);
    totalActions += Number(row?.metadata?.actionsPerformed || 0);
  }
  if (totalActions <= 0) return ["follow", "like", "comment"];

  const weighted = [
    { kind: "follow" as const, weight: follows / totalActions },
    { kind: "like" as const, weight: likes / totalActions },
    { kind: "comment" as const, weight: comments / totalActions },
  ].sort((a, b) => b.weight - a.weight);
  return weighted.map((w) => w.kind);
}

async function getActionsPerformedToday(): Promise<number> {
  const supabase = getSupabaseServer();
  if (!supabase) return 0;
  const dayStart = new Date();
  dayStart.setHours(0, 0, 0, 0);
  const { data, error } = await supabase
    .from("worker_run_logs")
    .select("metadata,started_at")
    .eq("worker_name", "social_growth")
    .gte("started_at", dayStart.toISOString())
    .order("started_at", { ascending: false })
    .limit(200);
  if (error || !data) return 0;
  return (data as any[]).reduce((sum, row) => {
    const val = Number(row?.metadata?.actions_performed || 0);
    return sum + (Number.isFinite(val) ? val : 0);
  }, 0);
}

function computeAllowedActionsByTime(now = new Date()): number {
  const dayStart = new Date(now);
  dayStart.setHours(0, 0, 0, 0);
  const elapsedMinutes = Math.max(0, Math.floor((now.getTime() - dayStart.getTime()) / 60000));
  const slotMinutes = Math.floor((24 * 60) / SOCIAL_DAILY_ACTION_TARGET);
  return Math.min(
    SOCIAL_DAILY_ACTION_TARGET,
    Math.max(1, Math.floor(elapsedMinutes / Math.max(slotMinutes, 1)) + 1),
  );
}

async function loadLeadHistoryMap(): Promise<Map<string, string | null>> {
  const map = new Map<string, string | null>();
  const supabase = getSupabaseServer();
  if (!supabase) return map;

  const { data } = await supabase
    .from("leads")
    .select("id,name,concept,notes")
    .order("created_at", { ascending: false })
    .limit(500);
  for (const row of (data || []) as LeadHistoryRow[]) {
    const handle = extractHandleFromText(row.concept) || extractHandleFromText(row.notes);
    if (!handle || map.has(handle)) continue;
    const historySnippet = (row.notes || "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(-10)
      .find((line) => !line.startsWith("[hunt_protocol]") && line.length > 20);
    map.set(handle, historySnippet || null);
  }
  return map;
}

function dedupeTargets(targets: SocialTarget[]): SocialTarget[] {
  const out: SocialTarget[] = [];
  const seen = new Set<string>();
  for (const t of targets) {
    if (seen.has(t.username)) continue;
    seen.add(t.username);
    out.push(t);
  }
  return out;
}

async function buildTargets(historyMap: Map<string, string | null>): Promise<{
  targets: SocialTarget[];
  scannedComments: number;
  classifiedDms: number;
  followSignals: number;
}> {
  const [scanOut, dmOut, followOut] = await Promise.all([
    runSocialRunner({ action: "scan", execute: false }),
    runSocialRunner({ action: "classify-dms", execute: false }),
    runSocialRunner({ action: "follow-back", execute: false }),
  ]);

  const targets: SocialTarget[] = [];
  for (const comment of scanOut.comments || []) {
    const username = normalizeUsername(comment.author);
    const text = String(comment.text || "");
    if (!username) continue;
    if (!looksLocalTattooSignal(text)) continue;
    targets.push({
      username,
      source: "comment_interest",
      reason: "local_tattoo_signal",
      historySnippet: historyMap.get(username) || null,
    });
  }

  for (const dm of dmOut.dms || []) {
    const username = normalizeUsername(dm.sender);
    if (!username) continue;
    if (String(dm.bucket || "") !== "inbound_lead") continue;
    targets.push({
      username,
      source: "dm_inbound",
      reason: "inbound_lead_bucket",
      historySnippet: historyMap.get(username) || String(dm.preview || "").slice(0, 180) || null,
    });
  }

  for (const follow of followOut.follow_backs || []) {
    const username = normalizeUsername(follow.username);
    if (!username) continue;
    targets.push({
      username,
      source: "follow_back",
      reason: String(follow.reason || "follow_signal"),
      historySnippet: historyMap.get(username) || null,
    });
  }

  return {
    targets: dedupeTargets(targets),
    scannedComments: (scanOut.comments || []).length,
    classifiedDms: (dmOut.dms || []).length,
    followSignals: (followOut.follow_backs || []).length,
  };
}

export async function runSocialGrowthWorker(): Promise<SocialGrowthRunResult> {
  const workerName = "social_growth";
  const runStartedAt = Date.now();
  const lock = await beginWorkerRun({
    workerName,
    intervalMinutes: WORKER_INTERVAL_MINUTES,
  });
  if (!lock.shouldRun) {
    return {
      scannedComments: 0,
      classifiedDms: 0,
      followSignals: 0,
      targetsConsidered: 0,
      actionsPlanned: 0,
      actionsPerformed: 0,
      greetingsSent: 0,
      likesPerformed: 0,
      commentsPerformed: 0,
      followsPerformed: 0,
      skipped: [{ username: "-", reason: lock.reason || "duplicate run" }],
    };
  }

  try {
    const historyMap = await loadLeadHistoryMap();
    const targetPack = await buildTargets(historyMap);
    const actionOrder = await computeActionPreferenceOrder();
    const actionsByNow = computeAllowedActionsByTime();
    const alreadyPerformed = await getActionsPerformedToday();
    const remainingForDay = Math.max(0, SOCIAL_DAILY_ACTION_TARGET - alreadyPerformed);
    const quotaOpenNow = Math.max(0, actionsByNow - alreadyPerformed);
    const actionBudget = Math.max(0, Math.min(remainingForDay, quotaOpenNow, MAX_ACTIONS_PER_RUN));
    const greetingBudget = Math.min(MAX_GREETINGS_PER_RUN, targetPack.targets.length);

    const skipped: SocialGrowthRunResult["skipped"] = [];
    let actionsPerformed = 0;
    let greetingsSent = 0;
    let likesPerformed = 0;
    let commentsPerformed = 0;
    let followsPerformed = 0;

    for (const target of targetPack.targets) {
      if (greetingsSent >= greetingBudget) break;
      const greeting = buildPhilosophyGreeting(target.username, target.historySnippet);
      const dmResult = await runSocialRunner({
        action: "send-dm",
        payload: { recipient: target.username, body: greeting },
        execute: true,
      }).catch((error: unknown) => ({
        posted: false,
        notes: [error instanceof Error ? error.message : "send-dm failed"],
      }));
      if (dmResult.posted) {
        greetingsSent += 1;
      } else {
        skipped.push({
          username: target.username,
          reason: `greeting_skipped:${(dmResult.notes || []).join(" | ") || "runner rejected"}`,
        });
      }
      await sleep(randomBetween(3500, 11000));
    }

    for (const target of targetPack.targets) {
      if (actionsPerformed >= actionBudget) break;
      for (const action of actionOrder) {
        if (actionsPerformed >= actionBudget) break;
        if (action === "follow") {
          const followResult = await runSocialRunner({
            action: "follow-user",
            payload: { recipient: target.username },
            execute: true,
          }).catch((error: unknown) => ({
            posted: false,
            notes: [error instanceof Error ? error.message : "follow-user failed"],
          }));
          if (followResult.posted) {
            actionsPerformed += 1;
            followsPerformed += 1;
          } else {
            skipped.push({
              username: target.username,
              reason: `follow_skipped:${(followResult.notes || []).join(" | ") || "runner rejected"}`,
            });
          }
          await sleep(randomBetween(6000, 22000));
          continue;
        }

        if (action === "like") {
          const likeResult = await runSocialRunner({
            action: "like-user",
            payload: { recipient: target.username },
            execute: true,
          }).catch((error: unknown) => ({
            posted: false,
            notes: [error instanceof Error ? error.message : "like-user failed"],
          }));
          if (likeResult.posted) {
            actionsPerformed += 1;
            likesPerformed += 1;
          } else {
            skipped.push({
              username: target.username,
              reason: `like_skipped:${(likeResult.notes || []).join(" | ") || "runner rejected"}`,
            });
          }
          await sleep(randomBetween(6000, 26000));
          continue;
        }

        const commentResult = await runSocialRunner({
          action: "comment-user",
          payload: { recipient: target.username, body: buildCommentText() },
          execute: true,
        }).catch((error: unknown) => ({
          posted: false,
          notes: [error instanceof Error ? error.message : "comment-user failed"],
        }));
        if (commentResult.posted) {
          actionsPerformed += 1;
          commentsPerformed += 1;
        } else {
          skipped.push({
            username: target.username,
            reason: `comment_skipped:${(commentResult.notes || []).join(" | ") || "runner rejected"}`,
          });
        }
        await sleep(randomBetween(8000, 28000));
      }
    }

    const result: SocialGrowthRunResult = {
      scannedComments: targetPack.scannedComments,
      classifiedDms: targetPack.classifiedDms,
      followSignals: targetPack.followSignals,
      targetsConsidered: targetPack.targets.length,
      actionsPlanned: actionBudget,
      actionsPerformed,
      greetingsSent,
      likesPerformed,
      commentsPerformed,
      followsPerformed,
      skipped,
    };

    await completeWorkerRun({
      workerName,
      runKey: lock.runKey,
      metadata: {
        ...result,
        duration_ms: Date.now() - runStartedAt,
      },
    });
    return result;
  } catch (error) {
    await failWorkerRun({
      workerName,
      runKey: lock.runKey,
      error: error instanceof Error ? error.message : "Unknown social growth error",
      metadata: {
        duration_ms: Date.now() - runStartedAt,
      },
    });
    throw error;
  }
}
