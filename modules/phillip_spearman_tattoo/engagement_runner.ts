/**
 * Phase 3 Engagement Runner — Playwright physical read/reply layer.
 *
 * DRY-RUN DEFAULT: scans and classifies only; live replies/follows blocked unless --execute.
 *
 * Actions:
 *   --action=scan          Parse notifications + comment sections
 *   --action=reply         Post a drafted reply (requires --execute)
 *   --action=classify-dms  Route DM previews into structural buckets
 *   --action=follow-back   Detect pending reciprocal follow targets
 *   --action=send-dm       Send Instagram DM (requires --payload=path, --execute for live)
 *
 * Phase 6 anti-ban safeguards (send-dm + execute):
 *   - 45–180s randomized delay before opening high-intent thread
 *   - 40–150ms per-keystroke typing simulation (no paste)
 *   - Strict outbound DM queue lock (one Playwright send at a time)
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, type Browser, type Locator, type Page } from "playwright";

import { acquireOutboundDmLock, releaseOutboundDmLock } from "./outbound_dm_queue.js";
import { humanPreThreadDelay, humanTypeText, randomBetween } from "./playwright_humanization.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const JARVIS_ROOT = resolve(__dirname, "../..");
const AUTH_DIR = join(JARVIS_ROOT, "data", "auth");

export type EngagementPlatform = "instagram" | "threads" | "tiktok";
export type EngagementAction =
  | "scan"
  | "reply"
  | "classify-dms"
  | "follow-back"
  | "send-dm"
  | "follow-user"
  | "like-user"
  | "comment-user";

const SESSION_FILES: Record<EngagementPlatform, string> = {
  instagram: join(AUTH_DIR, "instagram_session.json"),
  threads: join(AUTH_DIR, "threads_session.json"),
  tiktok: join(AUTH_DIR, "tiktok_session.json"),
};

const AUTH_COMMANDS: Record<EngagementPlatform, string> = {
  instagram: "npm run scrape -- --login",
  threads: "npm run auth -- --platform threads --force",
  tiktok: "npm run auth -- --platform tiktok --force",
};

const SCAN_URLS: Record<EngagementPlatform, string[]> = {
  instagram: [
    "https://www.instagram.com/accounts/activity/",
    "https://www.instagram.com/direct/inbox/",
  ],
  threads: [
    "https://www.threads.net/direct/inbox",
    "https://www.threads.net/activity",
  ],
  tiktok: [
    "https://www.tiktok.com/messages",
    "https://www.tiktok.com/",
  ],
};

/** Explicit inbox / message-list containers — wait for visibility before parsing. */
const MESSAGE_CONTAINER_SELECTORS: Record<EngagementPlatform, string[]> = {
  instagram: [
    '[aria-label="Thread list"]',
    '[role="listbox"]',
    'div[role="main"]',
  ],
  threads: [
    'div[role="main"]',
    '[role="list"]',
    'a[href*="/direct/t/"]',
    '[data-pressable-container="true"]',
  ],
  tiktok: [
    '[data-e2e="chat-list"]',
    '[data-e2e="chat-list-item"]',
    'div[class*="DivMessageList"]',
    'div[class*="MessageList"]',
  ],
};

const LOGIN_URL_FRAGMENTS = ["/login", "/signin", "/accounts/login"];
const LOGIN_TEXT_SIGNALS: Record<EngagementPlatform, RegExp[]> = {
  instagram: [/log in to instagram/i, /sign up to see/i],
  threads: [/log in with your instagram/i, /continue with instagram/i, /forgot password/i],
  tiktok: [/log in to tiktok/i, /sign up for tiktok/i, /use phone \/ email/i],
};

const UI_NOISE_PATTERNS: RegExp[] = [
  /^privacy policy$/i,
  /^terms of service$/i,
  /^threads terms$/i,
  /^consumer health privacy policy$/i,
  /^scan to get the app$/i,
  /^log in with/i,
  /^forgot password/i,
  /^continue with instagram$/i,
  /^trending$/i,
  /^discover$/i,
  /^newsroom$/i,
  /^programs$/i,
  /^tiktok for good$/i,
  /^advertise$/i,
  /^sell on tiktok shop$/i,
  /^tiktok live creator networks$/i,
  /^follow request$/i,
  /^liked your reel/i,
  /^\d+[mhd]\s*$/,
  /^primary$/i,
  /^general$/i,
  /^requests$/i,
  /^your note/i,
  /^what'?s new/i,
];

const MODAL_DISMISS_LABELS = [
  "Accept all",
  "Accept All",
  "Accept cookies",
  "Allow all",
  "Allow All",
  "Not Now",
  "Not now",
  "Continue in browser",
  "Continue in Browser",
  "Use web version",
  "Maybe later",
  "Skip",
  "Decline optional cookies",
  "Reject all",
  "Got it",
  "OK",
  "Close",
  "Dismiss",
  "I agree",
];

export interface ScannedComment {
  comment_id: string;
  author: string;
  text: string;
  post_ref: string;
  source: "notification" | "comment_section";
}

export interface ClassifiedDM {
  thread_id: string;
  sender: string;
  preview: string;
  bucket: "inbound_lead" | "existing_client" | "collaborator" | "general" | "spam";
}

export interface FollowBackCandidate {
  username: string;
  reason: string;
}

interface SendDmPayload {
  recipient: string;
  body: string;
}

interface FollowUserPayload {
  recipient: string;
}

interface LikeUserPayload {
  recipient: string;
}

interface CommentUserPayload {
  recipient: string;
  body: string;
}

interface RunnerOptions {
  action: EngagementAction;
  platform: EngagementPlatform;
  dryRun: boolean;
  headless: boolean;
  verbose: boolean;
  payloadPath: string | null;
}

function runnerLog(message: string, verbose: boolean): void {
  if (verbose) {
    console.error(`[RUNNER] ${message}`);
  }
}

class SessionExpiredError extends Error {
  constructor(public readonly platform: EngagementPlatform) {
    super(`Session expired for ${platform}`);
    this.name = "SessionExpiredError";
  }
}

function parseArgs(): RunnerOptions | null {
  const args = process.argv.slice(2);
  const actionRaw = args.find((a) => a.startsWith("--action="))?.split("=")[1];
  const platformRaw = args.find((a) => a.startsWith("--platform="))?.split("=")[1];

  const validActions: EngagementAction[] = [
    "scan",
    "reply",
    "classify-dms",
    "follow-back",
    "send-dm",
    "follow-user",
    "like-user",
    "comment-user",
  ];
  const validPlatforms: EngagementPlatform[] = ["instagram", "threads", "tiktok"];
  const payloadPath = args.find((a) => a.startsWith("--payload="))?.split("=")[1] ?? null;

  if (!actionRaw || !validActions.includes(actionRaw as EngagementAction)) {
    console.error(
      "Missing/invalid --action=scan|reply|classify-dms|follow-back|send-dm|follow-user|like-user|comment-user",
    );
    return null;
  }
  if (!platformRaw || !validPlatforms.includes(platformRaw as EngagementPlatform)) {
    console.error("Missing/invalid --platform=instagram|threads|tiktok");
    return null;
  }

  return {
    action: actionRaw as EngagementAction,
    platform: platformRaw as EngagementPlatform,
    dryRun: !args.includes("--execute"),
    headless: !args.includes("--headed"),
    verbose: args.includes("--verbose"),
    payloadPath,
  };
}

function printSessionExpiredHelp(platform: EngagementPlatform): void {
  console.error("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.error(`SESSION EXPIRED — ${platform.toUpperCase()}`);
  console.error("The saved session cannot reach the authenticated inbox.");
  console.error(`Re-authenticate with:\n  ${AUTH_COMMANDS[platform]}`);
  console.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
}

async function createSessionPage(
  platform: EngagementPlatform,
  headless: boolean,
): Promise<{ browser: Browser; page: Page }> {
  const sessionPath = SESSION_FILES[platform];
  if (!existsSync(sessionPath)) {
    console.error(`\nSession file missing for ${platform}: ${sessionPath}`);
    console.error(`Run: ${AUTH_COMMANDS[platform]}\n`);
    throw new SessionExpiredError(platform);
  }

  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({ storageState: sessionPath });
  const page = await context.newPage();
  return { browser, page };
}

function slugId(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 48) || "item";
}

function isUiNoise(line: string): boolean {
  const trimmed = line.trim();
  if (trimmed.length < 4) {
    return true;
  }
  return UI_NOISE_PATTERNS.some((pattern) => pattern.test(trimmed));
}

async function dismissIntrusiveModals(page: Page, platform: EngagementPlatform): Promise<void> {
  if (platform !== "threads" && platform !== "tiktok") {
    return;
  }

  for (let pass = 0; pass < 3; pass++) {
    for (const label of MODAL_DISMISS_LABELS) {
      const button = page.getByRole("button", { name: new RegExp(`^${label}$`, "i") }).first();
      const visible = await button.isVisible({ timeout: 400 }).catch(() => false);
      if (visible) {
        await button.click({ timeout: 2_000 }).catch(() => undefined);
        await page.waitForTimeout(400);
      }
    }

    for (const label of ["Not Now", "Continue in browser", "Accept"]) {
      const loose = page.locator(`button:has-text("${label}")`).first();
      const visible = await loose.isVisible({ timeout: 400 }).catch(() => false);
      if (visible) {
        await loose.click({ timeout: 2_000 }).catch(() => undefined);
        await page.waitForTimeout(400);
      }
    }
  }
}

async function assertSessionActive(page: Page, platform: EngagementPlatform): Promise<void> {
  const url = page.url().toLowerCase();
  if (LOGIN_URL_FRAGMENTS.some((fragment) => url.includes(fragment))) {
    printSessionExpiredHelp(platform);
    throw new SessionExpiredError(platform);
  }

  const bodyText = await page.locator("body").innerText({ timeout: 10_000 }).catch(() => "");
  if (LOGIN_TEXT_SIGNALS[platform].some((pattern) => pattern.test(bodyText))) {
    printSessionExpiredHelp(platform);
    throw new SessionExpiredError(platform);
  }
}

async function waitForMessageContainer(
  page: Page,
  platform: EngagementPlatform,
  strict: boolean,
): Promise<Locator | null> {
  const selectors = MESSAGE_CONTAINER_SELECTORS[platform];
  let lastError: unknown;

  for (const selector of selectors) {
    try {
      const container = page.locator(selector).first();
      await container.waitFor({ state: "visible", timeout: strict ? 20_000 : 8_000 });
      return container;
    } catch (error) {
      lastError = error;
    }
  }

  if (!strict) {
    return null;
  }

  await assertSessionActive(page, platform);
  printSessionExpiredHelp(platform);
  throw lastError ?? new SessionExpiredError(platform);
}

async function navigateInbox(page: Page, platform: EngagementPlatform): Promise<Locator> {
  const urls = SCAN_URLS[platform];
  let lastError: unknown;

  for (const inboxUrl of urls) {
    await page.goto(inboxUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForTimeout(1_500);
    await dismissIntrusiveModals(page, platform);

    try {
      await assertSessionActive(page, platform);
    } catch (error) {
      lastError = error;
      continue;
    }

    const container = await waitForMessageContainer(page, platform, false);
    if (container) {
      return container;
    }
  }

  await assertSessionActive(page, platform);
  printSessionExpiredHelp(platform);
  throw lastError ?? new SessionExpiredError(platform);
}

function parseDmLines(containerText: string, platform: EngagementPlatform): ClassifiedDM[] {
  const lines = parseLinesFromContainer(containerText);
  const dms: ClassifiedDM[] = [];

  for (const line of lines) {
    if (line.length < 6) {
      continue;
    }

    dms.push({
      thread_id: `${platform}_dm_${slugId(line)}`,
      sender: extractSenderFromLine(line),
      preview: line,
      bucket: classifyPreview(line),
    });

    if (dms.length >= 8) {
      break;
    }
  }

  return dms;
}

function parseLinesFromContainer(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length >= 4 && !isUiNoise(line));
}

async function extractCommentsFromPage(
  page: Page,
  platform: EngagementPlatform,
): Promise<ScannedComment[]> {
  const comments: ScannedComment[] = [];
  await dismissIntrusiveModals(page, platform);

  let sourceText = "";
  try {
    const container = await waitForMessageContainer(page, platform, false);
    sourceText = container
      ? await container.innerText({ timeout: 10_000 })
      : await page.locator("body").innerText().catch(() => "");
  } catch {
    sourceText = await page.locator("body").innerText().catch(() => "");
  }

  const lines = parseLinesFromContainer(sourceText);
  const keywords = ["commented", "replied", "mentioned", "said", "comment"];

  for (const line of lines) {
    const lower = line.toLowerCase();
    if (!keywords.some((word) => lower.includes(word))) {
      continue;
    }

    const authorMatch = line.match(/@([A-Za-z0-9._]+)/);
    const author = authorMatch?.[1] ?? "unknown";
    comments.push({
      comment_id: `${platform}_${slugId(author)}_${slugId(line)}`,
      author,
      text: line,
      post_ref: page.url(),
      source: "notification",
    });

    if (comments.length >= 10) {
      break;
    }
  }

  return comments;
}

async function scanComments(page: Page, platform: EngagementPlatform): Promise<ScannedComment[]> {
  const all: ScannedComment[] = [];

  for (const url of SCAN_URLS[platform]) {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForTimeout(1_500);
    await dismissIntrusiveModals(page, platform);
    all.push(...(await extractCommentsFromPage(page, platform)));
  }

  const seen = new Set<string>();
  return all.filter((item) => {
    if (seen.has(item.comment_id)) {
      return false;
    }
    seen.add(item.comment_id);
    return true;
  });
}

function classifyPreview(preview: string): ClassifiedDM["bucket"] {
  const lower = preview.toLowerCase();
  if (/spam|promo|crypto|onlyfans|follow back/.test(lower)) {
    return "spam";
  }
  if (/appointment|book|consult|quote|how much|pricing|slot/.test(lower)) {
    return "inbound_lead";
  }
  if (/touch.?up|healed|session|aftercare|my tattoo/.test(lower)) {
    return "existing_client";
  }
  if (/collab|guest spot|feature|press|brand/.test(lower)) {
    return "collaborator";
  }
  return "general";
}

function extractSenderFromLine(line: string): string {
  const handle = line.match(/@([A-Za-z0-9._]+)/);
  if (handle?.[1]) {
    return handle[1];
  }

  const word = line.split(/\s+/)[0]?.replace(/[^A-Za-z0-9._]/g, "");
  if (word && word.length >= 3 && word[0] === word[0]?.toUpperCase()) {
    return word.toLowerCase();
  }

  return "unknown";
}

async function classifyDMs(page: Page, platform: EngagementPlatform): Promise<ClassifiedDM[]> {
  if (platform === "threads" || platform === "tiktok") {
    const container = await navigateInbox(page, platform);
    const containerText = await container.innerText({ timeout: 10_000 });
    return parseDmLines(containerText, platform);
  }

  // Instagram — inbox with soft container fallback (activity notifications mixed in)
  await page.goto(SCAN_URLS.instagram[1], { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForTimeout(1_500);
  await dismissIntrusiveModals(page, platform);
  await assertSessionActive(page, platform);

  const container = await waitForMessageContainer(page, platform, false);
  const containerText = container
    ? await container.innerText({ timeout: 10_000 })
    : await page.locator("body").innerText({ timeout: 10_000 }).catch(() => "");

  return parseDmLines(containerText, platform);
}

async function scanFollowBacks(page: Page, platform: EngagementPlatform): Promise<FollowBackCandidate[]> {
  await page.goto(SCAN_URLS[platform][0], { waitUntil: "domcontentloaded", timeout: 60_000 });
  await page.waitForTimeout(1_500);
  await dismissIntrusiveModals(page, platform);
  await assertSessionActive(page, platform);

  let sourceText = "";
  try {
    const container = await waitForMessageContainer(page, platform, false);
    sourceText = container
      ? await container.innerText({ timeout: 10_000 })
      : await page.locator("body").innerText().catch(() => "");
  } catch {
    sourceText = await page.locator("body").innerText().catch(() => "");
  }

  const candidates: FollowBackCandidate[] = [];
  for (const line of parseLinesFromContainer(sourceText)) {
    const lower = line.toLowerCase();
    if (!lower.includes("follow")) {
      continue;
    }
    const userMatch = line.match(/@([A-Za-z0-9._]+)/);
    if (!userMatch) {
      continue;
    }
    candidates.push({
      username: userMatch[1],
      reason: lower.includes("followed you") ? "follow_back_pending" : "follow_signal",
    });
    if (candidates.length >= 5) {
      break;
    }
  }

  return candidates;
}

function loadSendDmPayload(payloadPath: string | null): SendDmPayload {
  if (!payloadPath) {
    throw new Error("send-dm requires --payload=/path/to/send_dm_payload.json");
  }
  if (!existsSync(payloadPath)) {
    throw new Error(`Payload file not found: ${payloadPath}`);
  }
  const raw = readFileSync(payloadPath, "utf-8");
  const parsed = JSON.parse(raw) as Partial<SendDmPayload>;
  if (!parsed.recipient || !parsed.body) {
    throw new Error("Payload must include recipient and body");
  }
  return { recipient: parsed.recipient.replace(/^@/, ""), body: parsed.body };
}

function loadRecipientPayload(payloadPath: string | null, action: string): FollowUserPayload {
  if (!payloadPath) {
    throw new Error(`${action} requires --payload=/path/to/payload.json`);
  }
  if (!existsSync(payloadPath)) {
    throw new Error(`Payload file not found: ${payloadPath}`);
  }
  const raw = readFileSync(payloadPath, "utf-8");
  const parsed = JSON.parse(raw) as Partial<FollowUserPayload>;
  if (!parsed.recipient) {
    throw new Error("Payload must include recipient");
  }
  return { recipient: parsed.recipient.replace(/^@/, "") };
}

function loadCommentPayload(payloadPath: string | null): CommentUserPayload {
  if (!payloadPath) {
    throw new Error("comment-user requires --payload=/path/to/payload.json");
  }
  if (!existsSync(payloadPath)) {
    throw new Error(`Payload file not found: ${payloadPath}`);
  }
  const raw = readFileSync(payloadPath, "utf-8");
  const parsed = JSON.parse(raw) as Partial<CommentUserPayload>;
  if (!parsed.recipient || !parsed.body) {
    throw new Error("Payload must include recipient and body");
  }
  return {
    recipient: parsed.recipient.replace(/^@/, ""),
    body: parsed.body,
  };
}

async function navigateInstagramProfile(page: Page, recipient: string): Promise<void> {
  await page.goto(`https://www.instagram.com/${recipient}/`, {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await page.waitForTimeout(1_200);
  await dismissIntrusiveModals(page, "instagram");
  await assertSessionActive(page, "instagram");
}

async function followInstagramUser(
  page: Page,
  recipient: string,
): Promise<{ posted: boolean; note: string }> {
  await navigateInstagramProfile(page, recipient);
  const followBtn = page
    .locator('button:has-text("Follow"), div[role="button"]:has-text("Follow")')
    .first();
  if ((await followBtn.count()) === 0) {
    return { posted: false, note: "follow button unavailable (already following/private/blocked)" };
  }
  await followBtn.click({ timeout: 5_000 }).catch(() => undefined);
  return { posted: true, note: `follow action attempted for @${recipient}` };
}

async function openLatestInstagramPost(page: Page): Promise<boolean> {
  const postLink = page.locator('a[href*="/p/"]').first();
  if ((await postLink.count()) === 0) return false;
  await postLink.click({ timeout: 8_000 }).catch(() => undefined);
  await page.waitForTimeout(700);
  return true;
}

async function likeInstagramUser(
  page: Page,
  recipient: string,
): Promise<{ posted: boolean; note: string }> {
  await navigateInstagramProfile(page, recipient);
  const opened = await openLatestInstagramPost(page);
  if (!opened) return { posted: false, note: "no post available to like" };
  const likeBtn = page
    .locator('svg[aria-label="Like"], div[role="button"] svg[aria-label="Like"]')
    .first();
  if ((await likeBtn.count()) === 0) {
    return { posted: false, note: "like control unavailable (already liked or UI mismatch)" };
  }
  await likeBtn.click({ timeout: 5_000 }).catch(() => undefined);
  return { posted: true, note: `like action attempted for @${recipient}` };
}

async function commentInstagramUser(
  page: Page,
  recipient: string,
  body: string,
): Promise<{ posted: boolean; note: string }> {
  await navigateInstagramProfile(page, recipient);
  const opened = await openLatestInstagramPost(page);
  if (!opened) return { posted: false, note: "no post available to comment on" };

  const commentBox = page
    .locator(
      'textarea[aria-label*="comment"], textarea[placeholder*="comment"], div[role="textbox"][aria-label*="comment"]',
    )
    .first();
  if ((await commentBox.count()) === 0) {
    return { posted: false, note: "comment box unavailable" };
  }
  await commentBox.click({ timeout: 5_000 });
  await commentBox.fill(body);
  await page.waitForTimeout(randomBetween(250, 700));

  const postBtn = page
    .locator('button:has-text("Post"), div[role="button"]:has-text("Post")')
    .first();
  if ((await postBtn.count()) > 0) {
    await postBtn.click({ timeout: 5_000 }).catch(() => undefined);
  } else {
    await page.keyboard.press("Enter").catch(() => undefined);
  }
  return { posted: true, note: `comment action attempted for @${recipient}` };
}

async function sendInstagramDm(
  page: Page,
  recipient: string,
  body: string,
  verbose: boolean,
): Promise<{ preThreadDelayMs: number; typingDelayMs: number }> {
  await page.goto("https://www.instagram.com/direct/inbox/", {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await page.waitForTimeout(1_500);
  await dismissIntrusiveModals(page, "instagram");
  await assertSessionActive(page, "instagram");

  const preThreadDelayMs = await humanPreThreadDelay(page, verbose, runnerLog);

  const newMessageSelectors = [
    'svg[aria-label="New message"]',
    'svg[aria-label="New Message"]',
    'div[role="button"]:has-text("Send message")',
  ];

  let opened = false;
  for (const selector of newMessageSelectors) {
    const trigger = page.locator(selector).first();
    if ((await trigger.count()) > 0) {
      await trigger.click({ timeout: 5_000 }).catch(() => undefined);
      opened = true;
      break;
    }
  }

  if (!opened) {
    await page.goto(`https://www.instagram.com/${recipient}/`, {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    await page.waitForTimeout(1_000);
    const messageBtn = page.locator('div[role="button"]:has-text("Message"), a:has-text("Message")').first();
    if ((await messageBtn.count()) > 0) {
      await messageBtn.click({ timeout: 8_000 });
    }
  } else {
    const searchInput = page.locator(
      'input[placeholder*="Search"], input[name="queryBox"], input[aria-label*="Search"]',
    ).first();
    await searchInput.waitFor({ state: "visible", timeout: 10_000 });
    await searchInput.fill(recipient);
    await page.waitForTimeout(1_200);
    const result = page.locator(`div[role="button"]:has-text("${recipient}")`).first();
    await result.click({ timeout: 8_000 });
    const chatButton = page.locator('div[role="button"]:has-text("Chat"), div[role="button"]:has-text("Next")').first();
    if ((await chatButton.count()) > 0) {
      await chatButton.click({ timeout: 5_000 }).catch(() => undefined);
    }
  }

  const composeSelectors = [
    'div[role="textbox"][contenteditable="true"]',
    'textarea[placeholder*="Message"]',
    'div[aria-label="Message"]',
  ];

  let compose: Locator | null = null;
  for (const selector of composeSelectors) {
    const candidate = page.locator(selector).last();
    if ((await candidate.count()) > 0) {
      compose = candidate;
      break;
    }
  }

  if (!compose) {
    throw new Error("Could not locate Instagram DM compose field");
  }

  const { totalDelayMs: typingDelayMs } = await humanTypeText(
    page,
    compose,
    body,
    verbose,
    runnerLog,
  );
  await page.waitForTimeout(randomBetween(400, 900));

  const sendSelectors = [
    'div[role="button"]:has-text("Send")',
    'button:has-text("Send")',
  ];
  for (const selector of sendSelectors) {
    const sendBtn = page.locator(selector).last();
    if ((await sendBtn.count()) > 0) {
      await sendBtn.click({ timeout: 5_000 });
      return { preThreadDelayMs, typingDelayMs };
    }
  }

  await page.keyboard.press("Enter");
  return { preThreadDelayMs, typingDelayMs };
}

async function runAction(options: RunnerOptions): Promise<Record<string, unknown>> {
  if (options.action === "follow-user") {
    const payload = loadRecipientPayload(options.payloadPath, "follow-user");
    if (options.dryRun) {
      return {
        posted: false,
        recipient: payload.recipient,
        notes: ["dry-run — follow-user suppressed (no Playwright launch)"],
      };
    }
    if (options.platform !== "instagram") {
      throw new Error(`follow-user not implemented for ${options.platform}`);
    }

    await acquireOutboundDmLock(options.verbose);
    const { browser, page } = await createSessionPage(options.platform, options.headless);
    try {
      const result = await followInstagramUser(page, payload.recipient);
      return { posted: result.posted, recipient: payload.recipient, notes: [result.note] };
    } finally {
      await browser.close();
      releaseOutboundDmLock(options.verbose);
    }
  }

  if (options.action === "like-user") {
    const payload = loadRecipientPayload(options.payloadPath, "like-user");
    if (options.dryRun) {
      return {
        posted: false,
        recipient: payload.recipient,
        notes: ["dry-run — like-user suppressed (no Playwright launch)"],
      };
    }
    if (options.platform !== "instagram") {
      throw new Error(`like-user not implemented for ${options.platform}`);
    }

    await acquireOutboundDmLock(options.verbose);
    const { browser, page } = await createSessionPage(options.platform, options.headless);
    try {
      const result = await likeInstagramUser(page, payload.recipient);
      return { posted: result.posted, recipient: payload.recipient, notes: [result.note] };
    } finally {
      await browser.close();
      releaseOutboundDmLock(options.verbose);
    }
  }

  if (options.action === "comment-user") {
    const payload = loadCommentPayload(options.payloadPath);
    if (options.dryRun) {
      return {
        posted: false,
        recipient: payload.recipient,
        body: payload.body,
        notes: ["dry-run — comment-user suppressed (no Playwright launch)"],
      };
    }
    if (options.platform !== "instagram") {
      throw new Error(`comment-user not implemented for ${options.platform}`);
    }

    await acquireOutboundDmLock(options.verbose);
    const { browser, page } = await createSessionPage(options.platform, options.headless);
    try {
      const result = await commentInstagramUser(page, payload.recipient, payload.body);
      return {
        posted: result.posted,
        recipient: payload.recipient,
        body: payload.body,
        notes: [result.note],
      };
    } finally {
      await browser.close();
      releaseOutboundDmLock(options.verbose);
    }
  }

  if (options.action === "send-dm") {
    const dmPayload = loadSendDmPayload(options.payloadPath);
    if (options.dryRun) {
      return {
        posted: false,
        recipient: dmPayload.recipient,
        body: dmPayload.body,
        notes: ["dry-run — send-dm suppressed (no Playwright launch)"],
      };
    }

    runnerLog(`Sending DM to @${dmPayload.recipient} on ${options.platform}`, options.verbose);
    await acquireOutboundDmLock(options.verbose);
    const { browser, page } = await createSessionPage(options.platform, options.headless);
    try {
      if (options.platform === "instagram") {
        const timing = await sendInstagramDm(
          page,
          dmPayload.recipient,
          dmPayload.body,
          options.verbose,
        );
        return {
          posted: true,
          recipient: dmPayload.recipient,
          body: dmPayload.body,
          pre_thread_delay_ms: timing.preThreadDelayMs,
          typing_delay_ms: timing.typingDelayMs,
          notes: [
            `sent DM to @${dmPayload.recipient} on ${options.platform}`,
            `pre-thread delay ${(timing.preThreadDelayMs / 1000).toFixed(1)}s`,
            `typing simulation ${timing.typingDelayMs}ms total`,
          ],
        };
      } else {
        throw new Error(`send-dm not implemented for ${options.platform}`);
      }
    } finally {
      await browser.close();
      releaseOutboundDmLock(options.verbose);
    }
  }

  runnerLog(`Launching Playwright (${options.platform}, action=${options.action})`, options.verbose);
  const { browser, page } = await createSessionPage(options.platform, options.headless);

  try {
    switch (options.action) {
      case "scan": {
        runnerLog(`Scanning comments + notifications on ${options.platform}`, options.verbose);
        const comments = await scanComments(page, options.platform);
        runnerLog(`Found ${comments.length} comment/notification(s)`, options.verbose);
        return { comments, notes: [`scanned ${comments.length} comment(s) on ${options.platform}`] };
      }
      case "classify-dms": {
        runnerLog(`Classifying DM inbox on ${options.platform}`, options.verbose);
        const dms = await classifyDMs(page, options.platform);
        runnerLog(`Classified ${dms.length} DM preview(s)`, options.verbose);
        return { dms, notes: [`classified ${dms.length} DM preview(s) on ${options.platform}`] };
      }
      case "follow-back": {
        runnerLog(`Scanning follow-back signals on ${options.platform}`, options.verbose);
        const follow_backs = await scanFollowBacks(page, options.platform);
        runnerLog(`Found ${follow_backs.length} follow signal(s)`, options.verbose);
        return {
          follow_backs,
          notes: [`found ${follow_backs.length} follow-back signal(s) on ${options.platform}`],
        };
      }
      case "reply": {
        if (options.dryRun) {
          return { posted: false, notes: ["dry-run — reply suppressed"] };
        }
        throw new Error("Live reply blocked. Pass --execute after manual review.");
      }
      default:
        throw new Error(`Unsupported action: ${options.action}`);
    }
  } finally {
    await browser.close();
  }
}

async function main(): Promise<void> {
  const options = parseArgs();
  if (!options) {
    process.exit(1);
  }

  const payload = await runAction(options);
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    if (error instanceof SessionExpiredError) {
      printSessionExpiredHelp(error.platform);
    } else {
      console.error(error);
    }
    process.exit(1);
  });
}
