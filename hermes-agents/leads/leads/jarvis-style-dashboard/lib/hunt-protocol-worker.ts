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
  lead_source: string | null;
  status: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface HuntProtocolRunResult {
  scanned: number;
  scored: number;
  contacted: number;
  channelBreakdown: { instagram: number; email: number; sms: number };
  skipped: { leadId: string; reason: string }[];
}

const DAILY_HUNT_TARGET = 12;
const HUNT_COOLDOWN_HOURS = 24;
const HUNT_MIN_SCORE = 55;
const HUNT_QUIET_HOURS_START = 21;
const HUNT_QUIET_HOURS_END = 8;
const CHANNEL_CAPS: Record<keyof HuntProtocolRunResult["channelBreakdown"], number> = {
  instagram: 6,
  email: 4,
  sms: 3,
};

function parseInstagramHandle(concept: string | null): string | null {
  const raw = concept || "";
  const m = raw.match(/@([a-zA-Z0-9._]+)/);
  return m ? `@${m[1]}` : null;
}

function buildHuntMessage(name: string): string {
  return `Hey ${name}, this is Elizabeth with Spearman Studio. I reviewed your concept and we can map your next tattoo session quickly. If you want, I can send your best slot options and next steps now.`;
}

function extractLastHuntSentAt(notes: string | null): Date | null {
  if (!notes) return null;
  const matches = Array.from(notes.matchAll(/\[hunt_protocol\]\s+contact_sent=([0-9T:.\-+Z]+)/g));
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

function resolveBestChannel(lead: LeadRow): keyof HuntProtocolRunResult["channelBreakdown"] | null {
  const ig = parseInstagramHandle(lead.concept);
  if (ig) return "instagram";
  if (lead.email) return "email";
  if (lead.phone) return "sms";
  return null;
}

function isQuietHoursNow(now = new Date()): boolean {
  const hour = now.getHours();
  return hour >= HUNT_QUIET_HOURS_START || hour < HUNT_QUIET_HOURS_END;
}

function scoreLead(lead: LeadRow): { score: number; reasons: string[] } {
  const reasons: string[] = [];
  let score = 0;

  const concept = (lead.concept || "").trim();
  const source = (lead.lead_source || "").toLowerCase();
  const ageMs = lead.created_at ? Date.now() - new Date(lead.created_at).getTime() : Number.POSITIVE_INFINITY;
  const ageDays = Number.isFinite(ageMs) ? ageMs / (24 * 60 * 60 * 1000) : 999;

  if (concept.length >= 60) {
    score += 30;
    reasons.push("high_intent_detail");
  } else if (concept.length >= 20) {
    score += 20;
    reasons.push("medium_intent_detail");
  } else if (concept.length > 0) {
    score += 10;
    reasons.push("low_intent_detail");
  }

  if (/@[a-zA-Z0-9._]+/.test(concept)) {
    score += 10;
    reasons.push("instagram_handle_present");
  }

  if (/deposit|book|appointment|session|ready|budget|consult/i.test(concept)) {
    score += 20;
    reasons.push("booking_intent_terms");
  }

  if (ageDays <= 1) {
    score += 20;
    reasons.push("fresh_lead_24h");
  } else if (ageDays <= 7) {
    score += 12;
    reasons.push("fresh_lead_7d");
  } else if (ageDays <= 14) {
    score += 6;
    reasons.push("fresh_lead_14d");
  }

  if (lead.email) score += 8;
  if (lead.phone) score += 8;

  if (/instagram|referral|website/.test(source)) {
    score += 10;
    reasons.push("high_quality_source");
  } else if (source) {
    score += 4;
    reasons.push("known_source");
  }

  return { score: Math.max(0, Math.min(100, score)), reasons };
}

export async function runHuntProtocolWorker(): Promise<HuntProtocolRunResult> {
  const workerName = "hunt_protocol";
  const runStartedAt = Date.now();
  const lock = await beginWorkerRun({
    workerName,
    intervalMinutes: 120,
  });
  if (!lock.shouldRun) {
    return {
      scanned: 0,
      scored: 0,
      contacted: 0,
      channelBreakdown: { instagram: 0, email: 0, sms: 0 },
      skipped: [{ leadId: "-", reason: lock.reason || "duplicate run" }],
    };
  }

  try {
  const supabase = getSupabaseServer();
  if (!supabase) {
    const result = {
      scanned: 0,
      scored: 0,
      contacted: 0,
      channelBreakdown: { instagram: 0, email: 0, sms: 0 },
      skipped: [],
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
  }

  const { data } = await supabase
    .from("leads")
    .select("id,name,email,phone,concept,lead_source,status,notes,created_at")
    .in("status", ["new", "Pending Review"])
    .order("created_at", { ascending: false })
    .limit(100);

  const leads = (data || []) as LeadRow[];
  const skipped: HuntProtocolRunResult["skipped"] = [];
  const channelBreakdown = { instagram: 0, email: 0, sms: 0 };
  let scored = 0;
  let contacted = 0;

  for (const lead of leads) {
    if (contacted >= DAILY_HUNT_TARGET) break;
    if (!lead.id) continue;
    if (isQuietHoursNow()) {
      skipped.push({ leadId: lead.id, reason: "Quiet hours stop condition (21:00-08:00)" });
      continue;
    }

    const channel = resolveBestChannel(lead);
    if (!channel) {
      skipped.push({ leadId: lead.id, reason: "No reachable channel" });
      continue;
    }
    if (channelBreakdown[channel] >= CHANNEL_CAPS[channel]) {
      skipped.push({ leadId: lead.id, reason: `Channel cap reached for ${channel}` });
      continue;
    }

    const scoredLead = scoreLead(lead);
    scored += 1;
    if (scoredLead.score < HUNT_MIN_SCORE) {
      skipped.push({
        leadId: lead.id,
        reason: `Lead score below threshold (${scoredLead.score}/${HUNT_MIN_SCORE})`,
      });
      continue;
    }

    const lastSentAt = extractLastHuntSentAt(lead.notes);
    if (isWithinCooldown(lastSentAt, HUNT_COOLDOWN_HOURS)) {
      skipped.push({ leadId: lead.id, reason: "Already contacted within 24h cooldown" });
      continue;
    }

    const name = (lead.name || "there").trim();
    const msg = buildHuntMessage(name);
    const ig = parseInstagramHandle(lead.concept);

    let ok = false;
    if (channel === "instagram" && ig) {
      const res = await sendOutboundMessage(ig, msg);
      ok = res.ok;
      if (ok) channelBreakdown.instagram += 1;
    } else if (channel === "email" && lead.email) {
      const res = await sendStudioEmail({
        to: lead.email,
        subject: "Spearman Studio — Next Steps",
        body: msg,
      });
      ok = res.ok;
      if (ok) channelBreakdown.email += 1;
    } else if (channel === "sms" && lead.phone) {
      const res = await sendStudioSms(lead.phone, msg);
      ok = res.ok;
      if (ok) channelBreakdown.sms += 1;
    }

    if (!ok) {
      skipped.push({ leadId: lead.id, reason: "Transport send failed" });
      continue;
    }

    contacted += 1;
    await supabase
      .from("leads")
      .update({
        status: "Approved - Awaiting Deposit",
        notes: `${lead.notes || ""}\n[hunt_protocol] contact_sent=${new Date().toISOString()} score=${scoredLead.score} reasons=${scoredLead.reasons.join(",")}`.trim(),
      })
      .eq("id", lead.id);
  }

  const result = {
    scanned: leads.length,
    scored,
    contacted,
    channelBreakdown,
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
      error: error instanceof Error ? error.message : "Unknown hunt protocol error",
      metadata: {
        duration_ms: Date.now() - runStartedAt,
      },
    });
    throw error;
  }
}
