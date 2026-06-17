import "server-only";
import { getSupabaseServer } from "@/lib/supabase-server";
import {
  beginWorkerRun,
  completeWorkerRun,
  failWorkerRun,
} from "@/lib/worker-run-log";

const DAILY_POST_TARGET = 20;

interface ContentRow {
  id: string;
  title: string | null;
  category: string | null;
  description: string | null;
  caption: string | null;
  status: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ContentSchedulerResult {
  scanned: number;
  dailyTarget: number;
  publishedToday: number;
  approvedToday: number;
  approvedQueued: number;
  pendingBefore: number;
  generated: number;
  pendingAfter: number;
  remainingShortfall: number;
}

interface ContentSchedulerOptions {
  dryRun?: boolean;
}

function toTag(raw: string): string {
  return raw
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join("");
}

function buildFiveHashtags(category: string, title: string, description: string): string[] {
  const map: Record<string, string[]> = {
    "black and grey": ["BlackAndGreyTattoo", "TattooArt", "InkLife"],
    "color": ["ColorTattoo", "TattooArt", "VibrantInk"],
    "japanese": ["JapaneseTattoo", "Irezumi", "TattooArt"],
    "korean": ["KoreanTattoo", "FineLineTattoo", "TattooArt"],
    "neo traditional": ["NeoTraditional", "TattooDesign", "InkLife"],
    "realism": ["RealismTattoo", "TattooArt", "InkWork"],
    "portraits": ["PortraitTattoo", "RealismTattoo", "TattooArt"],
    "sacred geometry": ["SacredGeometryTattoo", "GeometricTattoo", "TattooArt"],
    "sleeves and coverups": ["SleeveTattoo", "CoverUpTattoo", "TattooJourney"],
    "sleeves/coverups": ["SleeveTattoo", "CoverUpTattoo", "TattooJourney"],
  };
  const seed = map[category.trim().toLowerCase()] || ["TattooArt", "StudioWork", "InkLife"];
  const tokens = `${title} ${description}`
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 4)
    .slice(0, 3)
    .map(toTag);
  return Array.from(
    new Set([...seed, ...tokens, "PhillipSpearmanTattoo", "NorthridgeTattoo", "StudioScaling"]),
  )
    .slice(0, 5)
    .map((tag) => `#${tag}`);
}

function buildDraft(row: ContentRow): string {
  const title = (row.title || "New Tattoo Piece").trim();
  const category = (row.category || "Tattoo").trim();
  const description = (row.description || row.caption || "").trim();
  const caption = description
    ? `${title} — ${description}`
    : `${title} — ${category} piece prepared for posting review.`;
  const hashtags = buildFiveHashtags(category, title, description);
  return `${caption}\n\n${hashtags.join(" ")}`;
}

export async function runContentScheduler(
  options: ContentSchedulerOptions = {},
): Promise<ContentSchedulerResult> {
  const workerName = "content_scheduler";
  const runStartedAt = Date.now();
  const dryRun = Boolean(options.dryRun);
  const lock = dryRun
    ? { shouldRun: true, runKey: "dry_run" }
    : await beginWorkerRun({
        workerName,
        intervalMinutes: 60,
        metadata: { dryRun: false },
      });
  if (!lock.shouldRun) {
    return {
      scanned: 0,
      dailyTarget: DAILY_POST_TARGET,
      publishedToday: 0,
      approvedToday: 0,
      approvedQueued: 0,
      pendingBefore: 0,
      generated: 0,
      pendingAfter: 0,
      remainingShortfall: DAILY_POST_TARGET,
    };
  }

  try {
  const supabase = getSupabaseServer();
  if (!supabase) {
    const result = {
      scanned: 0,
      dailyTarget: DAILY_POST_TARGET,
      publishedToday: 0,
      approvedToday: 0,
      approvedQueued: 0,
      pendingBefore: 0,
      generated: 0,
      pendingAfter: 0,
      remainingShortfall: DAILY_POST_TARGET,
    };
    if (!dryRun) {
      await completeWorkerRun({
        workerName,
        runKey: lock.runKey,
        metadata: {
          ...result,
          duration_ms: Date.now() - runStartedAt,
        },
      });
    }
    return result;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayIso = today.toISOString();

  const [{ count: publishedToday }, { count: approvedQueued }, { count: pendingBefore }, { data: allRows }] = await Promise.all([
    supabase
      .from("content_vault")
      .select("*", { count: "exact", head: true })
      .eq("status", "published")
      .gte("updated_at", todayIso),
    supabase
      .from("content_vault")
      .select("*", { count: "exact", head: true })
      .eq("status", "approved"),
    supabase
      .from("content_vault")
      .select("*", { count: "exact", head: true })
      .eq("status", "pending_review"),
    supabase
      .from("content_vault")
      .select("id,title,category,description,caption,status,created_at,updated_at")
      .order("created_at", { ascending: false }),
  ]);

  const publishedCount = publishedToday || 0;
  const approvedQueuedCount = approvedQueued || 0;
  const pendingCount = pendingBefore || 0;
  const slotsNeeded = Math.max(
    DAILY_POST_TARGET - publishedCount - approvedQueuedCount - pendingCount,
    0,
  );

  let generated = 0;
  let staleRefreshed = 0;
  const candidates = (allRows || []) as ContentRow[];
  const nowIso = new Date().toISOString();
  const staleCutoffMs = 48 * 60 * 60 * 1000;

  // Refresh stale pending drafts before generating net-new ones.
  for (const row of candidates) {
    if (staleRefreshed >= 10) break;
    if (row.status !== "pending_review") continue;
    if (!row.updated_at) continue;
    const ageMs = Date.now() - new Date(row.updated_at).getTime();
    if (ageMs < staleCutoffMs) continue;
    if (dryRun) {
      staleRefreshed += 1;
      continue;
    }
    const refreshed = buildDraft(row);
    const { error } = await supabase
      .from("content_vault")
      .update({ caption: refreshed, description: refreshed, updated_at: nowIso })
      .eq("id", row.id);
    if (!error) staleRefreshed += 1;
  }

  if (slotsNeeded > 0) {
    for (const row of candidates) {
      if (!row?.id) continue;
      if (row.status === "pending_review" || row.status === "approved") continue;
      if (dryRun) {
        generated += 1;
        if (generated >= slotsNeeded) break;
        continue;
      }
      const draft = buildDraft(row);
      const { error } = await supabase
        .from("content_vault")
        .update({ caption: draft, description: draft, status: "pending_review", updated_at: nowIso })
        .eq("id", row.id);
      if (!error) {
        generated += 1;
      }
      if (generated >= slotsNeeded) break;
    }
  }

  const pendingAfter = pendingCount + generated;
  const result = {
    scanned: candidates.length,
    dailyTarget: DAILY_POST_TARGET,
    publishedToday: publishedCount,
    approvedToday: publishedCount,
    approvedQueued: approvedQueuedCount,
    pendingBefore: pendingCount,
    generated,
    pendingAfter,
    remainingShortfall: Math.max(
      DAILY_POST_TARGET - publishedCount - approvedQueuedCount - pendingAfter,
      0,
    ),
  };
  if (!dryRun) {
    await completeWorkerRun({
      workerName,
      runKey: lock.runKey,
      metadata: {
        ...result,
        staleRefreshed,
        duration_ms: Date.now() - runStartedAt,
      },
    });
  }
  return result;
  } catch (error) {
    if (!dryRun) {
      await failWorkerRun({
        workerName,
        runKey: lock.runKey,
        error: error instanceof Error ? error.message : "Unknown scheduler error",
        metadata: {
          duration_ms: Date.now() - runStartedAt,
        },
      });
    }
    throw error;
  }
}
