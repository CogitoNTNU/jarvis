import "server-only";
import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseServer } from "@/lib/supabase-server";

type WorkerRunStatus = "started" | "completed" | "failed";

interface WorkerRunFallbackRecord {
  worker: string;
  runKey: string;
  status: WorkerRunStatus;
  ts: string;
  metadata?: Record<string, unknown>;
  error?: string;
}

export interface WorkerRunStartResult {
  shouldRun: boolean;
  runKey: string;
  reason?: string;
}

export interface WorkerRunSnapshot {
  worker: string;
  runKey: string;
  status: WorkerRunStatus;
  ts: string;
}

export interface WorkerRunSummary {
  worker: string;
  completed: number;
  failed: number;
  started: number;
  duplicate: number;
}

interface DuplicateRecordParams {
  workerName: string;
  runKey: string;
  reason?: string;
  metadata?: Record<string, unknown>;
}

const RETRY_DELAYS_MS = [100, 250, 500];
const FALLBACK_SESSION_ID = "__worker_run_fallback__";
const FALLBACK_PREFIX = "[worker_run_fallback]";

function getServerSupabaseOrThrow(): SupabaseClient {
  const supabase = getSupabaseServer();
  if (!supabase) {
    throw new Error(
      "Supabase server client unavailable. Check NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY.",
    );
  }
  return supabase;
}

function isMissingWorkerRunTableError(message: string): boolean {
  return (
    /worker_run_logs/i.test(message) &&
    (/could not find the table/i.test(message) ||
      /relation .* does not exist/i.test(message) ||
      /schema cache/i.test(message))
  );
}

function isDuplicateKeyError(message: string): boolean {
  return /duplicate key|unique constraint|23505/i.test(message);
}

async function withRetry<T>(fn: () => Promise<T>): Promise<T> {
  let lastError: unknown;
  for (let i = 0; i <= RETRY_DELAYS_MS.length; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (i < RETRY_DELAYS_MS.length) {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS_MS[i]));
      }
    }
  }
  throw lastError;
}

function floorToInterval(date: Date, intervalMinutes: number): Date {
  const ms = intervalMinutes * 60 * 1000;
  const floored = Math.floor(date.getTime() / ms) * ms;
  return new Date(floored);
}

function buildRunKey(workerName: string, intervalMinutes: number, date = new Date()): string {
  const bucket = floorToInterval(date, intervalMinutes).toISOString();
  return `${workerName}:${bucket}`;
}

function encodeFallback(record: WorkerRunFallbackRecord): string {
  return `${FALLBACK_PREFIX}:${JSON.stringify(record)}`;
}

function decodeFallback(content: string): WorkerRunFallbackRecord | null {
  if (!content.startsWith(`${FALLBACK_PREFIX}:`)) return null;
  const raw = content.slice(FALLBACK_PREFIX.length + 1);
  try {
    const parsed = JSON.parse(raw) as WorkerRunFallbackRecord;
    if (!parsed?.worker || !parsed?.runKey || !parsed?.status) return null;
    return parsed;
  } catch {
    return null;
  }
}

async function readFallbackRun(
  supabase: SupabaseClient,
  worker: string,
  runKey: string,
): Promise<WorkerRunFallbackRecord | null> {
  const { data, error } = await withRetry(async () =>
    supabase
      .from("message_store")
      .select("message,created_at")
      .eq("session_id", FALLBACK_SESSION_ID)
      .order("created_at", { ascending: false })
      .limit(400),
  );
  if (error || !data) return null;
  for (const row of data as any[]) {
    const content = String(row?.message?.data?.content || "");
    const parsed = decodeFallback(content);
    if (!parsed) continue;
    if (parsed.worker === worker && parsed.runKey === runKey) return parsed;
  }
  return null;
}

async function writeFallbackRun(
  supabase: SupabaseClient,
  record: WorkerRunFallbackRecord,
): Promise<void> {
  const payload = {
    session_id: FALLBACK_SESSION_ID,
    message: { type: "ai", data: { content: encodeFallback(record) } },
  };
  await withRetry(async () => supabase.from("message_store").insert(payload));
}

export async function recordWorkerRunDuplicate(params: DuplicateRecordParams): Promise<void> {
  const supabase = getServerSupabaseOrThrow();
  const now = new Date().toISOString();

  const { data, error } = await withRetry(async () =>
    supabase
      .from("worker_run_logs")
      .select("metadata")
      .eq("worker_name", params.workerName)
      .eq("run_key", params.runKey)
      .maybeSingle(),
  );

  if (!error) {
    const current = ((data as any)?.metadata || {}) as Record<string, unknown>;
    const duplicateRuns = Number(current.duplicate_runs || 0);
    const metadata = {
      ...current,
      ...(params.metadata || {}),
      duplicate_runs: Number.isFinite(duplicateRuns) ? duplicateRuns + 1 : 1,
      last_duplicate_reason: params.reason || "duplicate_run_key",
      last_duplicate_at: now,
    };
    await withRetry(async () =>
      supabase
        .from("worker_run_logs")
        .update({
          metadata,
          updated_at: now,
        })
        .eq("worker_name", params.workerName)
        .eq("run_key", params.runKey),
    );
    return;
  }

  if (!isMissingWorkerRunTableError(error.message)) {
    throw new Error(`recordWorkerRunDuplicate failed: ${error.message}`);
  }

  const existing = await readFallbackRun(supabase, params.workerName, params.runKey);
  const duplicateRuns = Number(existing?.metadata?.duplicate_runs || 0);
  await writeFallbackRun(supabase, {
    worker: params.workerName,
    runKey: params.runKey,
    status: existing?.status || "started",
    ts: now,
    metadata: {
      ...(existing?.metadata || {}),
      ...(params.metadata || {}),
      duplicate_runs: Number.isFinite(duplicateRuns) ? duplicateRuns + 1 : 1,
      last_duplicate_reason: params.reason || "duplicate_run_key",
      last_duplicate_at: now,
    },
  });
}

export async function beginWorkerRun(params: {
  workerName: string;
  intervalMinutes: number;
  metadata?: Record<string, unknown>;
}): Promise<WorkerRunStartResult> {
  const supabase = getServerSupabaseOrThrow();
  const runKey = buildRunKey(params.workerName, params.intervalMinutes);
  const startedAt = new Date().toISOString();

  const payload = {
    worker_name: params.workerName,
    run_key: runKey,
    status: "started",
    started_at: startedAt,
    metadata: params.metadata || {},
  };

  const { error } = await withRetry(async () => supabase.from("worker_run_logs").insert(payload));
  if (!error) {
    return { shouldRun: true, runKey };
  }

  if (isDuplicateKeyError(error.message)) {
    await recordWorkerRunDuplicate({
      workerName: params.workerName,
      runKey,
      reason: "duplicate_run_key",
      metadata: params.metadata,
    });
    return { shouldRun: false, runKey, reason: "duplicate_run_key" };
  }

  if (!isMissingWorkerRunTableError(error.message)) {
    throw new Error(`beginWorkerRun failed: ${error.message}`);
  }

  const existing = await readFallbackRun(supabase, params.workerName, runKey);
  if (existing && (existing.status === "started" || existing.status === "completed")) {
    await recordWorkerRunDuplicate({
      workerName: params.workerName,
      runKey,
      reason: `fallback_${existing.status}`,
      metadata: params.metadata,
    });
    return { shouldRun: false, runKey, reason: `fallback_${existing.status}` };
  }
  await writeFallbackRun(supabase, {
    worker: params.workerName,
    runKey,
    status: "started",
    ts: startedAt,
    metadata: params.metadata,
  });
  return { shouldRun: true, runKey };
}

export async function completeWorkerRun(params: {
  workerName: string;
  runKey: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  const supabase = getServerSupabaseOrThrow();
  const finishedAt = new Date().toISOString();
  const { error } = await withRetry(async () =>
    supabase
      .from("worker_run_logs")
      .update({
        status: "completed",
        finished_at: finishedAt,
        metadata: params.metadata || {},
      })
      .eq("worker_name", params.workerName)
      .eq("run_key", params.runKey),
  );
  if (!error) return;
  if (!isMissingWorkerRunTableError(error.message)) {
    throw new Error(`completeWorkerRun failed: ${error.message}`);
  }
  await writeFallbackRun(supabase, {
    worker: params.workerName,
    runKey: params.runKey,
    status: "completed",
    ts: finishedAt,
    metadata: params.metadata,
  });
}

export async function failWorkerRun(params: {
  workerName: string;
  runKey: string;
  error: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  const supabase = getServerSupabaseOrThrow();
  const finishedAt = new Date().toISOString();
  const { error } = await withRetry(async () =>
    supabase
      .from("worker_run_logs")
      .update({
        status: "failed",
        finished_at: finishedAt,
        error_message: params.error,
        metadata: params.metadata || {},
      })
      .eq("worker_name", params.workerName)
      .eq("run_key", params.runKey),
  );
  if (!error) return;
  if (!isMissingWorkerRunTableError(error.message)) {
    throw new Error(`failWorkerRun failed: ${error.message}`);
  }
  await writeFallbackRun(supabase, {
    worker: params.workerName,
    runKey: params.runKey,
    status: "failed",
    ts: finishedAt,
    metadata: params.metadata,
    error: params.error,
  });
}

export async function getLatestWorkerRunSnapshots(
  workerNames: string[],
): Promise<WorkerRunSnapshot[]> {
  const supabase = getServerSupabaseOrThrow();
  const uniqWorkers = Array.from(new Set(workerNames.filter(Boolean)));
  if (!uniqWorkers.length) return [];

  const { data, error } = await withRetry(async () =>
    supabase
      .from("worker_run_logs")
      .select("worker_name,run_key,status,started_at,finished_at")
      .in("worker_name", uniqWorkers)
      .order("started_at", { ascending: false })
      .limit(200),
  );

  if (!error && data) {
    const byWorker = new Map<string, WorkerRunSnapshot>();
    for (const row of data as any[]) {
      const worker = String(row?.worker_name || "");
      if (!worker || byWorker.has(worker)) continue;
      byWorker.set(worker, {
        worker,
        runKey: String(row?.run_key || ""),
        status: (row?.status || "started") as WorkerRunStatus,
        ts: String(row?.finished_at || row?.started_at || new Date().toISOString()),
      });
    }
    return uniqWorkers
      .map((worker) => byWorker.get(worker))
      .filter((v): v is WorkerRunSnapshot => Boolean(v));
  }

  if (error && !isMissingWorkerRunTableError(error.message)) {
    throw new Error(`getLatestWorkerRunSnapshots failed: ${error.message}`);
  }

  const { data: fallbackRows } = await withRetry(async () =>
    supabase
      .from("message_store")
      .select("message,created_at")
      .eq("session_id", FALLBACK_SESSION_ID)
      .order("created_at", { ascending: false })
      .limit(500),
  );
  const byWorker = new Map<string, WorkerRunSnapshot>();
  for (const row of (fallbackRows || []) as any[]) {
    const content = String(row?.message?.data?.content || "");
    const parsed = decodeFallback(content);
    if (!parsed) continue;
    if (!uniqWorkers.includes(parsed.worker)) continue;
    if (byWorker.has(parsed.worker)) continue;
    byWorker.set(parsed.worker, {
      worker: parsed.worker,
      runKey: parsed.runKey,
      status: parsed.status,
      ts: parsed.ts || String(row?.created_at || new Date().toISOString()),
    });
  }
  return uniqWorkers
    .map((worker) => byWorker.get(worker))
    .filter((v): v is WorkerRunSnapshot => Boolean(v));
}

export async function getWorkerRunSummary(
  workerNames: string[],
  hoursBack: number = 24,
): Promise<WorkerRunSummary[]> {
  const supabase = getServerSupabaseOrThrow();
  const uniqWorkers = Array.from(new Set(workerNames.filter(Boolean)));
  if (!uniqWorkers.length) return [];

  const since = new Date(Date.now() - Math.max(hoursBack, 1) * 60 * 60 * 1000).toISOString();
  const { data, error } = await withRetry(async () =>
    supabase
      .from("worker_run_logs")
      .select("worker_name,status,metadata,started_at")
      .in("worker_name", uniqWorkers)
      .gte("started_at", since)
      .order("started_at", { ascending: false }),
  );

  if (!error && data) {
    const summaryMap = new Map<string, WorkerRunSummary>();
    for (const worker of uniqWorkers) {
      summaryMap.set(worker, {
        worker,
        completed: 0,
        failed: 0,
        started: 0,
        duplicate: 0,
      });
    }
    for (const row of data as any[]) {
      const worker = String(row?.worker_name || "");
      if (!summaryMap.has(worker)) continue;
      const bucket = summaryMap.get(worker)!;
      const status = String(row?.status || "started");
      if (status === "completed") bucket.completed += 1;
      else if (status === "failed") bucket.failed += 1;
      else bucket.started += 1;
      const duplicateCount = Number((row?.metadata || {})?.duplicate_runs || 0);
      if (Number.isFinite(duplicateCount) && duplicateCount > 0) {
        bucket.duplicate += duplicateCount;
      }
    }
    return uniqWorkers.map((worker) => summaryMap.get(worker)!);
  }

  if (error && !isMissingWorkerRunTableError(error.message)) {
    throw new Error(`getWorkerRunSummary failed: ${error.message}`);
  }

  const fallbackRows = await withRetry(async () =>
    supabase
      .from("message_store")
      .select("message,created_at")
      .eq("session_id", FALLBACK_SESSION_ID)
      .order("created_at", { ascending: false })
      .limit(600),
  );
  const summaryMap = new Map<string, WorkerRunSummary>();
  for (const worker of uniqWorkers) {
    summaryMap.set(worker, {
      worker,
      completed: 0,
      failed: 0,
      started: 0,
      duplicate: 0,
    });
  }
  if ((fallbackRows as any)?.error) return uniqWorkers.map((w) => summaryMap.get(w)!);

  for (const row of ((fallbackRows as any)?.data || []) as any[]) {
    const parsed = decodeFallback(String(row?.message?.data?.content || ""));
    if (!parsed) continue;
    if (!summaryMap.has(parsed.worker)) continue;
    const bucket = summaryMap.get(parsed.worker)!;
    if (parsed.status === "completed") bucket.completed += 1;
    else if (parsed.status === "failed") bucket.failed += 1;
    else bucket.started += 1;
  }
  return uniqWorkers.map((worker) => summaryMap.get(worker)!);
}
