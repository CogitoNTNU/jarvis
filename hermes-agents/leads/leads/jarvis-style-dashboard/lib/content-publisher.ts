import "server-only";
import { getSupabaseServer } from "@/lib/supabase-server";
import { beginWorkerRun, completeWorkerRun, failWorkerRun } from "@/lib/worker-run-log";

interface PublishCandidate {
  id: string;
  title: string | null;
  category: string | null;
  image_path: string | null;
  status: string | null;
}

export interface ContentPublisherResult {
  scanned: number;
  published: number;
  failed: number;
  skipped: { id: string; reason: string }[];
}

const PUBLISH_BATCH_LIMIT = 20;

function isMissingColumnError(message: string): boolean {
  return /column .* does not exist/i.test(message);
}

async function markAsPublished(
  supabase: NonNullable<ReturnType<typeof getSupabaseServer>>,
  row: PublishCandidate,
  publishedAt: string,
): Promise<{ ok: boolean; reason?: string }> {
  const syntheticPostId = `sim_${row.id}_${Date.now()}`;
  const payload = {
    status: "published",
    updated_at: publishedAt,
    published_at: publishedAt,
    publish_status: "published",
    publish_channel: "instagram",
    external_post_id: syntheticPostId,
    publish_error: null,
  };

  const { error } = await supabase.from("content_vault").update(payload).eq("id", row.id);
  if (!error) return { ok: true };

  if (!isMissingColumnError(error.message)) {
    return { ok: false, reason: error.message };
  }

  const fallback = await supabase
    .from("content_vault")
    .update({
      status: "published",
      updated_at: publishedAt,
    })
    .eq("id", row.id);
  if (fallback.error) {
    return { ok: false, reason: fallback.error.message };
  }
  return { ok: true };
}

export async function runContentPublisher(): Promise<ContentPublisherResult> {
  const workerName = "content_publisher";
  const runStartedAt = Date.now();
  const lock = await beginWorkerRun({
    workerName,
    intervalMinutes: 30,
  });
  if (!lock.shouldRun) {
    return {
      scanned: 0,
      published: 0,
      failed: 0,
      skipped: [{ id: "-", reason: lock.reason || "duplicate run" }],
    };
  }

  try {
    const supabase = getSupabaseServer();
    if (!supabase) {
      const result = { scanned: 0, published: 0, failed: 0, skipped: [] };
      await completeWorkerRun({
        workerName,
        runKey: lock.runKey,
        metadata: {
          ...result,
          duration_ms: Date.now() - runStartedAt,
        },
      });
      return result;
    }

    const { data } = await supabase
      .from("content_vault")
      .select("id,title,category,image_path,status")
      .eq("status", "approved")
      .order("updated_at", { ascending: true })
      .limit(PUBLISH_BATCH_LIMIT);

    const rows = (data || []) as PublishCandidate[];
    const skipped: ContentPublisherResult["skipped"] = [];
    let published = 0;
    let failed = 0;

    for (const row of rows) {
      if (!row.id) continue;
      if (!row.image_path) {
        skipped.push({ id: row.id, reason: "Missing image path" });
        continue;
      }
      const publishedAt = new Date().toISOString();
      const publishResult = await markAsPublished(supabase, row, publishedAt);
      if (!publishResult.ok) {
        failed += 1;
        skipped.push({ id: row.id, reason: publishResult.reason || "Publish update failed" });
        continue;
      }
      published += 1;
    }

    const result = {
      scanned: rows.length,
      published,
      failed,
      skipped,
    };
    await completeWorkerRun({
      workerName,
      runKey: lock.runKey,
      metadata: {
        ...result,
        skippedCount: skipped.length,
        duration_ms: Date.now() - runStartedAt,
      },
    });
    return result;
  } catch (error) {
    await failWorkerRun({
      workerName,
      runKey: lock.runKey,
      error: error instanceof Error ? error.message : "Unknown content publisher error",
      metadata: {
        duration_ms: Date.now() - runStartedAt,
      },
    });
    throw error;
  }
}
