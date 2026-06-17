"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";

type WorkerSummary = {
  worker: string;
  completed: number;
  failed: number;
  started: number;
  duplicate: number;
};

type Payload = {
  ok: boolean;
  generatedAt?: string;
  content?: {
    dailyTarget: number;
    publishedToday: number;
    approvedToday: number;
    approvedQueued: number;
    pendingBefore: number;
    pendingAfter: number;
    generated: number;
    remainingShortfall: number;
  };
  workers?: {
    snapshots: Array<{ worker: string; status: string; ts: string }>;
    summary24h: WorkerSummary[];
  };
  error?: string;
};

export function OpsMetricsPanel() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<Payload | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/system/ops-metrics", { cache: "no-store" });
      const data = (await res.json()) as Payload;
      if (!res.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      setPayload(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load ops metrics.");
      setPayload(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const content = payload?.content;
  const workerSummaries = payload?.workers?.summary24h || [];
  const snapshots = payload?.workers?.snapshots || [];

  const statusByWorker = useMemo(() => {
    return new Map(snapshots.map((s) => [s.worker, s.status]));
  }, [snapshots]);

  return (
    <div className="border border-cyan-950 bg-black/50 p-4 flex flex-col min-h-0">
      <div className="flex items-center justify-between border-b border-cyan-950 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-3 h-3 text-cyan-400" />
          <h3 className="text-[10px] uppercase tracking-widest text-cyan-400 font-mono">
            AUTONOMY OPS METRICS
          </h3>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="text-cyan-400 hover:text-cyan-200 disabled:opacity-40"
          disabled={isLoading}
          title="Refresh ops metrics"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {error && (
        <div className="border border-red-900/60 bg-red-950/20 p-2 text-[10px] text-red-300 font-mono mb-3">
          {error}
        </div>
      )}

      {!error && content && (
        <div className="border border-cyan-950 bg-black/30 p-2 mb-3 space-y-1">
          <p className="text-[9px] text-cyan-300 font-mono uppercase tracking-wider">
            Content Daily Target: {content.dailyTarget}
          </p>
          <p className="text-[9px] text-slate-300 font-mono">
            Published: {content.publishedToday} | Approved Queue: {content.approvedQueued} | Pending: {content.pendingAfter}
          </p>
          <p className="text-[9px] text-amber-300 font-mono">
            Remaining Shortfall: {content.remainingShortfall}
          </p>
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
        {workerSummaries.map((row) => (
          <div key={row.worker} className="border border-cyan-950 bg-black/30 p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[9px] uppercase tracking-wider text-cyan-300 font-mono">
                {row.worker.replace(/_/g, " ")}
              </span>
              <span className="text-[8px] text-slate-500 font-mono">
                {statusByWorker.get(row.worker) || "unknown"}
              </span>
            </div>
            <p className="text-[9px] text-slate-300 font-mono">
              24h — done:{row.completed} failed:{row.failed} running:{row.started} dupes:{row.duplicate}
            </p>
          </div>
        ))}
        {!error && workerSummaries.length === 0 && !isLoading && (
          <div className="border border-cyan-950 bg-black/30 p-2 text-[10px] text-slate-400 font-mono">
            No worker metrics available yet.
          </div>
        )}
      </div>
    </div>
  );
}
