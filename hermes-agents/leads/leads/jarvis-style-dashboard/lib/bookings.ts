import "server-only";
import { randomUUID } from "node:crypto";
import { getSupabaseServer } from "@/lib/supabase-server";
import { TIME_SLOT_LABELS, resolveAppBaseUrl } from "@/lib/studio-config";
import { DEPOSIT_AMOUNT_CENTS, getStripe } from "@/lib/stripe";
import {
  formatAppointmentDate,
} from "@/lib/nurture-messages";
import { STRIPE_CHECKOUT_BRANDING, STRIPE_WALLET_OPTIONS } from "@/lib/studio-theme";
import { resolveDepositGatewayUrl } from "@/lib/deposit-link";
import { sendApprovalToOriginalChannel, resolveOriginalChannel } from "@/lib/communication";
import { assertLifecycleTransition } from "@/lib/lead-lifecycle";

export type BookingStatus =
  | "Pending Review"
  | "Approved - Awaiting Deposit"
  | "Booked"
  | "Completed"
  | "Rejected";

export type CommunicationChannel = "instagram" | "email" | "sms" | "form";

export interface BookingRecord {
  id: string;
  client_name: string;
  email: string;
  phone: string | null;
  instagram_handle: string | null;
  tattoo_style: string | null;
  concept: string | null;
  status: BookingStatus;
  original_channel: CommunicationChannel;
  stripe_session_id: string | null;
  stripe_checkout_url: string | null;
  deposit_paid: boolean;
  appointment_date: string;
  appointment_time_label: string;
  time_slot_id: string | null;
  preferred_days: string[] | null;
  calendar_locked: boolean;
  approval_sent_at: string | null;
  approval_channel: CommunicationChannel | null;
  confirm_received_at: string | null;
  escalation_email_sent_at: string | null;
  escalation_sms_sent_at: string | null;
  nurture_7day_sent_at: string | null;
  nurture_3day_sent_at: string | null;
  nurture_24hr_sent_at: string | null;
  google_calendar_event_id: string | null;
  google_calendar_event_link: string | null;
  consent_completed_at: string | null;
  consent_data: ConsentRecord | null;
  parent_booking_id: string | null;
  completion_record: CompletionRecord | null;
  follow_up_check_at: string | null;
  follow_up_check_sent_at: string | null;
  follow_up_calendar_event_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsentRecord {
  signedName: string;
  ageConfirmed: boolean;
  healthDisclosure: string;
  depositPolicyAccepted: boolean;
  photoReleaseAccepted: boolean;
  signedAt: string;
}

export interface CompletionRecord {
  amountPaid: number;
  stored: string;
  description: string;
  photoDataUrls: string[];
  completedAt: string;
}

export interface IntakeWebhookPayload {
  firstName?: string;
  lastName?: string;
  name?: string;
  email?: string;
  phone?: string;
  instagram?: string;
  instagram_handle?: string;
  social_handle?: string;
  handle?: string;
  tattooStyle?: string;
  style?: string;
  description?: string;
  concept?: string;
  preferredDays?: string[];
  timeSlot?: string;
  appointmentDate?: string;
  channel?: string;
  lead_source?: string;
}

const DAY_INDEX: Record<string, number> = {
  sunday: 0, monday: 1, tuesday: 2, wednesday: 3,
  thursday: 4, friday: 5, saturday: 6,
};

function encodeLeadNotes(booking: BookingRecord): string {
  return JSON.stringify({ phase7: true, phase7_booking: booking });
}

export function decodeLeadNotes(notes: string | null | undefined): BookingRecord | null {
  if (!notes) return null;
  try {
    const parsed = JSON.parse(notes) as { phase7_booking?: BookingRecord };
    return parsed.phase7_booking || null;
  } catch {
    return null;
  }
}

async function persistLeadBooking(booking: BookingRecord): Promise<void> {
  const supabase = getSupabaseServer();
  if (!supabase) return;

  const conceptText = [
    booking.tattoo_style ? `Style: ${booking.tattoo_style}` : null,
    booking.concept,
    booking.preferred_days?.length ? `Preferred: ${booking.preferred_days.join(", ")}` : null,
    `Requested slot: ${booking.appointment_time_label}`,
    `Appointment: ${booking.appointment_date}`,
  ].filter(Boolean).join("\n");

  const { data: existing } = await supabase
    .from("leads")
    .select("id")
    .eq("email", booking.email)
    .maybeSingle();

  const row = {
    name: booking.client_name,
    email: booking.email,
    phone: booking.phone || "—",
    concept: conceptText,
    lead_source: booking.original_channel === "instagram" ? "social_intake" : "external_form",
    status: booking.status,
    notes: encodeLeadNotes(booking),
  };

  if (existing?.id) {
    await supabase.from("leads").update(row).eq("id", existing.id);
  } else {
    await supabase.from("leads").insert(row);
  }
}

function inferChannel(body: IntakeWebhookPayload, instagramHandle: string | null): CommunicationChannel {
  const raw = (body.channel || body.lead_source || "").toLowerCase();
  if (raw.includes("instagram") || raw === "dm") return "instagram";
  if (instagramHandle) return "instagram";
  if (raw.includes("sms") || raw.includes("text")) return "sms";
  if (raw.includes("email")) return "email";
  return "form";
}

export function normalizeIntakePayload(body: IntakeWebhookPayload) {
  const firstName = body.firstName?.trim() || "";
  const lastName = body.lastName?.trim() || "";
  const clientName =
    body.name?.trim() ||
    [firstName, lastName].filter(Boolean).join(" ") ||
    "New Client";

  const email = body.email?.trim().toLowerCase();
  if (!email) throw new Error("email is required");

  const rawHandle =
    body.instagram_handle || body.instagram || body.social_handle || body.handle || "";
  const instagramHandle = rawHandle
    ? rawHandle.startsWith("@") ? rawHandle : `@${rawHandle.replace(/^@/, "")}`
    : null;

  const tattooStyle = body.tattooStyle || body.style || null;
  const concept = body.description || body.concept || null;
  const preferredDays = body.preferredDays?.length ? body.preferredDays : null;
  const timeSlot = body.timeSlot || "afternoon";
  const appointmentTimeLabel = TIME_SLOT_LABELS[timeSlot] || timeSlot || "TBD";
  const appointmentDate =
    body.appointmentDate ||
    computeNextPreferredDate(preferredDays || ["monday", "tuesday", "wednesday", "thursday", "friday"]);
  const originalChannel = inferChannel(body, instagramHandle);

  return {
    clientName, email, phone: body.phone?.trim() || null, instagramHandle,
    tattooStyle, concept, preferredDays, timeSlot, appointmentTimeLabel,
    appointmentDate, originalChannel,
  };
}

function computeNextPreferredDate(preferredDayIds: string[]): string {
  const targets = preferredDayIds.map((d) => DAY_INDEX[d.toLowerCase()]).filter((n) => n !== undefined);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  if (!targets.length) {
    const f = new Date(today);
    f.setDate(f.getDate() + 14);
    return f.toISOString();
  }
  for (let offset = 1; offset <= 21; offset++) {
    const c = new Date(today);
    c.setDate(c.getDate() + offset);
    if (targets.includes(c.getDay())) return c.toISOString();
  }
  const f = new Date(today);
  f.setDate(f.getDate() + 14);
  return f.toISOString();
}

export async function createPendingReviewLead(
  normalized: ReturnType<typeof normalizeIntakePayload>,
  bookingId: string = randomUUID(),
): Promise<BookingRecord> {
  const now = new Date().toISOString();
  const booking: BookingRecord = {
    id: bookingId,
    client_name: normalized.clientName,
    email: normalized.email,
    phone: normalized.phone,
    instagram_handle: normalized.instagramHandle,
    tattoo_style: normalized.tattooStyle,
    concept: normalized.concept,
    status: "Pending Review",
    original_channel: normalized.originalChannel,
    stripe_session_id: null,
    stripe_checkout_url: null,
    deposit_paid: false,
    appointment_date: normalized.appointmentDate,
    appointment_time_label: normalized.appointmentTimeLabel,
    time_slot_id: normalized.timeSlot,
    preferred_days: normalized.preferredDays,
    calendar_locked: false,
    approval_sent_at: null,
    approval_channel: null,
    confirm_received_at: null,
    escalation_email_sent_at: null,
    escalation_sms_sent_at: null,
    nurture_7day_sent_at: null,
    nurture_3day_sent_at: null,
    nurture_24hr_sent_at: null,
    google_calendar_event_id: null,
    google_calendar_event_link: null,
    consent_completed_at: null,
    consent_data: null,
    parent_booking_id: null,
    completion_record: null,
    follow_up_check_at: null,
    follow_up_check_sent_at: null,
    follow_up_calendar_event_id: null,
    created_at: now,
    updated_at: now,
  };

  const supabase = getSupabaseServer();
  if (supabase) {
    const { error } = await supabase.from("bookings").insert(booking);
    if (error) {
      console.warn("[BOOKINGS] bookings insert skipped:", error.message);
    }
    await persistLeadBooking(booking);
  }

  return booking;
}

export async function listLeadsForReview(): Promise<BookingRecord[]> {
  const supabase = getSupabaseServer();
  if (!supabase) return [];

  const { data: bookings } = await supabase
    .from("bookings")
    .select("*")
    .order("created_at", { ascending: false });

  let leads: BookingRecord[] = [];
  if (bookings?.length) {
    leads = bookings as BookingRecord[];
  } else {
    const { data: rows } = await supabase
      .from("leads")
      .select("notes, created_at")
      .order("created_at", { ascending: false });

    leads = (rows || [])
      .map((r) => decodeLeadNotes(r.notes as string))
      .filter((b): b is BookingRecord => Boolean(b));
  }

  const byId = new Map<string, BookingRecord>();
  for (const lead of leads) {
    const existing = byId.get(lead.id);
    if (!existing || lead.updated_at > existing.updated_at) {
      byId.set(lead.id, lead);
    }
  }

  return [...byId.values()].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

export async function getBookingById(id: string): Promise<BookingRecord | null> {
  const supabase = getSupabaseServer();
  if (!supabase) return null;

  const { data } = await supabase.from("bookings").select("*").eq("id", id).maybeSingle();
  if (data) return data as BookingRecord;

  const { data: leads } = await supabase.from("leads").select("notes").ilike("notes", `%${id}%`);
  for (const row of leads || []) {
    const b = decodeLeadNotes(row.notes as string);
    if (b?.id === id) return b;
  }
  return null;
}

export async function getBookingByStripeSession(sessionId: string): Promise<BookingRecord | null> {
  const supabase = getSupabaseServer();
  if (!supabase) return null;

  const { data } = await supabase.from("bookings").select("*").eq("stripe_session_id", sessionId).maybeSingle();
  if (data) return data as BookingRecord;

  const { data: leads } = await supabase.from("leads").select("notes").ilike("notes", `%${sessionId}%`);
  for (const row of leads || []) {
    const b = decodeLeadNotes(row.notes as string);
    if (b?.stripe_session_id === sessionId) return b;
  }
  return null;
}

async function createStripeSessionAndSend(
  existing: BookingRecord,
  bookingId: string,
  opts: { appointmentDate: string; appointmentTimeLabel: string; timeSlotId?: string },
  status: BookingStatus,
): Promise<{ booking: BookingRecord; sendResult: { ok: boolean; channel: string; message: string } }> {
  const baseUrl = resolveAppBaseUrl();
  const stripe = getStripe();
  const now = new Date().toISOString();

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ["card"],
    customer_email: existing.email,
    line_items: [{
      price_data: {
        currency: "usd",
        unit_amount: DEPOSIT_AMOUNT_CENTS,
        product_data: {
          name: `Tattoo Session Deposit — ${existing.client_name}`,
          description: "Non-refundable deposit to secure your session at Spearman Studio.",
        },
      },
      quantity: 1,
    }],
    mode: "payment",
    ui_mode: "embedded",
    redirect_on_completion: "if_required",
    return_url: `${baseUrl}/success?session_id={CHECKOUT_SESSION_ID}`,
    metadata: {
      booking_id: bookingId,
      client_email: existing.email,
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    branding_settings: STRIPE_CHECKOUT_BRANDING as any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    wallet_options: STRIPE_WALLET_OPTIONS as any,
  });

  const channel = resolveOriginalChannel(existing);
  const depositLinkUrl = resolveDepositGatewayUrl(bookingId);
  const messageCtx = {
    clientName: existing.client_name,
    tattooStyle: existing.tattoo_style || undefined,
    appointmentDateLabel: formatAppointmentDate(opts.appointmentDate),
    appointmentTimeLabel: opts.appointmentTimeLabel,
    checkoutUrl: session.url || undefined,
    depositLinkUrl,
  };

  const sendResult = await sendApprovalToOriginalChannel(existing, messageCtx);

  const updated: BookingRecord = {
    ...existing,
    status,
    appointment_date: opts.appointmentDate,
    appointment_time_label: opts.appointmentTimeLabel,
    time_slot_id: opts.timeSlotId || existing.time_slot_id,
    stripe_session_id: session.id,
    stripe_checkout_url: session.url,
    approval_sent_at: now,
    approval_channel: channel,
    confirm_received_at: null,
    escalation_email_sent_at: null,
    escalation_sms_sent_at: null,
    updated_at: now,
  };
  assertLifecycleTransition(existing.status, updated.status, "approveLead");

  const supabase = getSupabaseServer();
  if (supabase) {
    await supabase.from("bookings").update({
      status: updated.status,
      appointment_date: updated.appointment_date,
      appointment_time_label: updated.appointment_time_label,
      stripe_session_id: updated.stripe_session_id,
      stripe_checkout_url: updated.stripe_checkout_url,
      approval_sent_at: updated.approval_sent_at,
      approval_channel: updated.approval_channel,
      confirm_received_at: null,
      escalation_email_sent_at: null,
      escalation_sms_sent_at: null,
      updated_at: updated.updated_at,
    }).eq("id", bookingId);
    await persistLeadBooking(updated);
  }

  return {
    booking: updated,
    sendResult: { ok: sendResult.ok, channel: sendResult.channel, message: sendResult.message },
  };
}

export async function approveLead(
  bookingId: string,
  opts: { appointmentDate: string; appointmentTimeLabel: string; timeSlotId?: string },
): Promise<{ booking: BookingRecord; sendResult: { ok: boolean; channel: string; message: string } }> {
  const existing = await getBookingById(bookingId);
  if (!existing) throw new Error("Lead not found");
  if (existing.status !== "Pending Review") {
    throw new Error(`Lead status is ${existing.status}, expected Pending Review`);
  }

  return createStripeSessionAndSend(existing, bookingId, opts, "Approved - Awaiting Deposit");
}

export async function resendDepositLink(
  bookingId: string,
  opts: { appointmentDate: string; appointmentTimeLabel: string; timeSlotId?: string },
): Promise<{ booking: BookingRecord; sendResult: { ok: boolean; channel: string; message: string } }> {
  const existing = await getBookingById(bookingId);
  if (!existing) throw new Error("Lead not found");
  if (existing.status !== "Approved - Awaiting Deposit") {
    throw new Error(`Lead status is ${existing.status}, expected Approved - Awaiting Deposit`);
  }
  if (existing.deposit_paid) {
    throw new Error("Deposit already paid — lead is booked");
  }

  return createStripeSessionAndSend(existing, bookingId, opts, "Approved - Awaiting Deposit");
}

export async function resetLeadToPendingReview(bookingId: string): Promise<BookingRecord> {
  const existing = await getBookingById(bookingId);
  if (!existing) throw new Error("Lead not found");
  if (existing.deposit_paid) {
    throw new Error("Cannot reset a booked lead");
  }

  const updated: BookingRecord = {
    ...existing,
    status: "Pending Review",
    stripe_session_id: null,
    stripe_checkout_url: null,
    approval_sent_at: null,
    approval_channel: null,
    confirm_received_at: null,
    escalation_email_sent_at: null,
    escalation_sms_sent_at: null,
    updated_at: new Date().toISOString(),
  };
  assertLifecycleTransition(existing.status, updated.status, "resetLeadToPendingReview");

  const supabase = getSupabaseServer();
  if (supabase) {
    await supabase.from("bookings").update({
      status: "Pending Review",
      stripe_session_id: null,
      stripe_checkout_url: null,
      approval_sent_at: null,
      approval_channel: null,
      confirm_received_at: null,
      escalation_email_sent_at: null,
      escalation_sms_sent_at: null,
      updated_at: updated.updated_at,
    }).eq("id", bookingId);
    await persistLeadBooking(updated);
  }

  return updated;
}

export async function markConfirmReceived(bookingId: string): Promise<BookingRecord | null> {
  const existing = await getBookingById(bookingId);
  if (!existing) return null;

  const updated: BookingRecord = {
    ...existing,
    confirm_received_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  await persistLeadBooking(updated);
  const supabase = getSupabaseServer();
  if (supabase) {
    await supabase.from("bookings").update({
      confirm_received_at: updated.confirm_received_at,
      updated_at: updated.updated_at,
    }).eq("id", bookingId);
  }
  return updated;
}

export async function markBookingPaid(bookingId: string): Promise<BookingRecord | null> {
  const existing = await getBookingById(bookingId);
  if (!existing) return null;

  const now = new Date().toISOString();
  const updated: BookingRecord = {
    ...existing,
    status: "Booked",
    deposit_paid: true,
    calendar_locked: true,
    updated_at: now,
  };
  assertLifecycleTransition(existing.status, updated.status, "markBookingPaid");

  const supabase = getSupabaseServer();
  if (supabase) {
    await supabase.from("bookings").update({
      status: "Booked", deposit_paid: true, calendar_locked: true, updated_at: now,
    }).eq("id", bookingId);
    await persistLeadBooking(updated);
  }
  return updated;
}

export async function listBookedForNurture(): Promise<BookingRecord[]> {
  const supabase = getSupabaseServer();
  if (!supabase) return [];

  const { data } = await supabase.from("bookings").select("*").eq("status", "Booked").eq("deposit_paid", true);
  if (data?.length) return data as BookingRecord[];

  const { data: leads } = await supabase.from("leads").select("notes").eq("status", "Booked");
  return (leads || [])
    .map((r) => decodeLeadNotes(r.notes as string))
    .filter((b): b is BookingRecord => Boolean(b && b.deposit_paid));
}

export async function listAwaitingEscalation(): Promise<BookingRecord[]> {
  const all = await listLeadsForReview();
  return all.filter((b) => b.status === "Approved - Awaiting Deposit" && b.approval_sent_at);
}

export async function updateEscalationTimestamps(
  bookingId: string,
  patch: Partial<Pick<BookingRecord, "escalation_email_sent_at" | "escalation_sms_sent_at">>,
): Promise<void> {
  const existing = await getBookingById(bookingId);
  if (!existing) return;
  const updated = { ...existing, ...patch, updated_at: new Date().toISOString() };
  await persistLeadBooking(updated);
}

export async function markNurtureSent(bookingId: string, stage: "7day" | "3day" | "24hr"): Promise<void> {
  const existing = await getBookingById(bookingId);
  if (!existing) return;
  const col = stage === "7day" ? "nurture_7day_sent_at" : stage === "3day" ? "nurture_3day_sent_at" : "nurture_24hr_sent_at";
  const updated = { ...existing, [col]: new Date().toISOString(), updated_at: new Date().toISOString() };
  await persistLeadBooking(updated);
}

export async function updateBookingCalendarMeta(
  bookingId: string,
  patch: Partial<Pick<BookingRecord, "google_calendar_event_id" | "google_calendar_event_link" | "calendar_locked">>,
): Promise<void> {
  const existing = await getBookingById(bookingId);
  if (!existing) return;
  const updated = { ...existing, ...patch, updated_at: new Date().toISOString() };
  await persistLeadBooking(updated);
}

export async function markConsentCompleted(
  bookingId: string,
  consent: ConsentRecord,
): Promise<BookingRecord | null> {
  const existing = await getBookingById(bookingId);
  if (!existing) return null;
  const updated: BookingRecord = {
    ...existing,
    consent_completed_at: consent.signedAt,
    consent_data: consent,
    updated_at: new Date().toISOString(),
  };
  await persistLeadBooking(updated);
  return updated;
}

// Legacy alias
export const createPendingBooking = createPendingReviewLead;

async function saveBooking(booking: BookingRecord): Promise<void> {
  const supabase = getSupabaseServer();
  if (!supabase) return;

  await supabase.from("bookings").upsert(booking, { onConflict: "id" }).then(({ error }) => {
    if (error) console.warn("[BOOKINGS] upsert skipped:", error.message);
  });
  await persistLeadBooking(booking);
}

export async function bookAnotherSession(
  parentBookingId: string,
  opts: { appointmentDate: string; appointmentTimeLabel: string; timeSlotId?: string },
): Promise<{ booking: BookingRecord; sendResult: { ok: boolean; channel: string; message: string } }> {
  const parent = await getBookingById(parentBookingId);
  if (!parent) throw new Error("Lead not found");
  if (parent.status !== "Booked" && parent.status !== "Completed") {
    throw new Error(`Cannot book another session from status: ${parent.status}`);
  }

  const now = new Date().toISOString();
  const newId = randomUUID();
  const pending: BookingRecord = {
    ...parent,
    id: newId,
    status: "Pending Review",
    parent_booking_id: parentBookingId,
    stripe_session_id: null,
    stripe_checkout_url: null,
    deposit_paid: false,
    appointment_date: opts.appointmentDate,
    appointment_time_label: opts.appointmentTimeLabel,
    time_slot_id: opts.timeSlotId || parent.time_slot_id,
    calendar_locked: false,
    approval_sent_at: null,
    approval_channel: null,
    confirm_received_at: null,
    escalation_email_sent_at: null,
    escalation_sms_sent_at: null,
    nurture_7day_sent_at: null,
    nurture_3day_sent_at: null,
    nurture_24hr_sent_at: null,
    google_calendar_event_id: null,
    google_calendar_event_link: null,
    consent_completed_at: null,
    consent_data: null,
    completion_record: null,
    follow_up_check_at: null,
    follow_up_check_sent_at: null,
    follow_up_calendar_event_id: null,
    created_at: now,
    updated_at: now,
  };
  const supabase = getSupabaseServer();
  if (supabase) {
    const { error } = await supabase.from("bookings").insert(pending);
    if (error) console.warn("[BOOKINGS] another-session insert:", error.message);
    await persistLeadBooking(pending);
  }

  return createStripeSessionAndSend(
    pending,
    newId,
    opts,
    "Approved - Awaiting Deposit",
  );
}

export async function completeTattooSession(
  bookingId: string,
  completion: Omit<CompletionRecord, "completedAt">,
  followUpCheckAt: string,
  followUpCalendarEventId?: string | null,
): Promise<BookingRecord> {
  const existing = await getBookingById(bookingId);
  if (!existing) throw new Error("Lead not found");
  if (existing.status !== "Booked") {
    throw new Error(`Lead status is ${existing.status}, expected Booked`);
  }

  const now = new Date().toISOString();
  const updated: BookingRecord = {
    ...existing,
    status: "Completed",
    completion_record: {
      ...completion,
      completedAt: now,
    },
    follow_up_check_at: followUpCheckAt,
    follow_up_check_sent_at: null,
    follow_up_calendar_event_id: followUpCalendarEventId || null,
    updated_at: now,
  };
  assertLifecycleTransition(existing.status, updated.status, "completeTattooSession");

  await saveBooking(updated);
  return updated;
}

export async function listForFollowUpCheck(): Promise<BookingRecord[]> {
  const all = await listLeadsForReview();
  const now = Date.now();
  return all.filter(
    (b) =>
      b.status === "Completed" &&
      b.follow_up_check_at &&
      !b.follow_up_check_sent_at &&
      new Date(b.follow_up_check_at).getTime() <= now,
  );
}

export async function markFollowUpCheckSent(bookingId: string): Promise<void> {
  const existing = await getBookingById(bookingId);
  if (!existing) return;
  const updated: BookingRecord = {
    ...existing,
    follow_up_check_sent_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  await saveBooking(updated);
}
