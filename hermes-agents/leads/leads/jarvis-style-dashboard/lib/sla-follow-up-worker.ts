import "server-only";
import { getSupabaseServer } from "@/lib/supabase-server";
import { sendStudioEmail } from "@/lib/email-transport";
import { sendStudioSms } from "@/lib/sms-transport";
import { sendOutboundMessage } from "@/lib/outbound-transport";
import { beginWorkerRun, completeWorkerRun, failWorkerRun } from "@/lib/worker-run-log";

interface LeadRow {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  concept: string | null;
  status: string | null;
  notes: string | null;
  updated_at: string | null;
}

export interface SlaFollowUpResult {
  scanned: number;
  sent: number;
  skipped: { leadId: string; reason: string }[];
}

const SLA_HOURS = 12;
const FOLLOW_UP_COOLDOWN_HOURS = 24;

function extractHandle(raw: string | null): string | null {
  const m = (raw || "").match(/@([a-zA-Z0-9._]+)/);
  return m ? `@${m[1]}` : null;
}

function isOverdue(updatedAt: string | null): boolean {
  if (!updatedAt) return true;
  const ageMs = Date.now() - new Date(updatedAt).getTime();
  return ageMs >= SLA_HOURS * 60 * 60 * 1000;
}

function buildFollowUp(name: string): string {
  return `Hey ${name}, quick follow-up from Spearman Studio. I reviewed your previous message and can move this forward now with best slot options and next-step details whenever you're ready.`;
}

function extractLastSlaFollowUpAt(notes: string | null): Date | null {
  if (!notes) return null;
  const matches = Array.from(notes.matchAll(/\[sla_follow_up\]\s+sent=([0-9T:.\-+Z]+)/g));
  if (!matches.length) return null;
  const raw = matches[matches.length - 1]?.[1];
  if (!raw) return null;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function isWithinCooldown(lastSentAt: Date | null, hours: number): boolean {
  if (!lastSentAt) return false;
  const ageMs = Date.now() - lastSentAt.getTime();
  return ageMs < hours * 60 * 60 * 1000;
}

export async function runSlaFollowUpWorker(): Promise<SlaFollowUpResult> {
  const workerName = "sla_follow_up";
  const runStartedAt = Date.now();
  const lock = await beginWorkerRun({
    workerName,
    intervalMinutes: 60,
  });
  if (!lock.shouldRun) {
    return {
      scanned: 0,
      sent: 0,
      skipped: [{ leadId: "-", reason: lock.reason || "duplicate run" }],
    };
  }

  try {
  const supabase = getSupabaseServer();
  if (!supabase) {
    const result = { scanned: 0, sent: 0, skipped: [] };
    await completeWorkerRun({
      workerName,
      runKey: lock.runKey,
      metadata: {
        ...result,
        skippedCount: result.skipped.length,
        duration_ms: Date.now() - runStartedAt,
      },
    });
    return result;
  }

  const { data } = await supabase
    .from("leads")
    .select("id,name,email,phone,concept,status,notes,updated_at")
    .in("status", ["new", "Pending Review", "Approved - Awaiting Deposit"])
    .order("updated_at", { ascending: true })
    .limit(150);

  const leads = ((data || []) as LeadRow[]).filter((l) => isOverdue(l.updated_at));
  const skipped: SlaFollowUpResult["skipped"] = [];
  let sent = 0;

  for (const lead of leads) {
    const lastSentAt = extractLastSlaFollowUpAt(lead.notes);
    if (isWithinCooldown(lastSentAt, FOLLOW_UP_COOLDOWN_HOURS)) {
      skipped.push({ leadId: lead.id, reason: "SLA follow-up already sent in last 24h" });
      continue;
    }

    const name = (lead.name || "there").trim();
    const text = buildFollowUp(name);
    const handle = extractHandle(lead.concept);
    let ok = false;

    if (handle) {
      ok = (await sendOutboundMessage(handle, text)).ok;
    } else if (lead.email) {
      ok = (
        await sendStudioEmail({
          to: lead.email,
          subject: "Spearman Studio — Follow-up",
          body: text,
        })
      ).ok;
    } else if (lead.phone) {
      ok = (await sendStudioSms(lead.phone, text)).ok;
    } else {
      skipped.push({ leadId: lead.id, reason: "No reachable channel" });
      continue;
    }

    if (!ok) {
      skipped.push({ leadId: lead.id, reason: "Transport send failed" });
      continue;
    }

    sent += 1;
    await supabase
      .from("leads")
      .update({
        notes: `${lead.notes || ""}\n[sla_follow_up] sent=${new Date().toISOString()}`.trim(),
      })
      .eq("id", lead.id);
  }

  const result = {
    scanned: leads.length,
    sent,
    skipped,
  };
  await completeWorkerRun({
    workerName,
    runKey: lock.runKey,
    metadata: {
      ...result,
      skippedCount: result.skipped.length,
      duration_ms: Date.now() - runStartedAt,
    },
  });
  return result;
  } catch (error) {
    await failWorkerRun({
      workerName,
      runKey: lock.runKey,
      error: error instanceof Error ? error.message : "Unknown SLA follow-up error",
      metadata: {
        duration_ms: Date.now() - runStartedAt,
      },
    });
    throw error;
  }
}
