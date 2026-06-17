/**
 * Social growth automation worker (run via cron).
 *
 * Example crontab (hourly):
 * 0 * * * * cd /path/to/jarvis-style-dashboard && CRON_SECRET=xxx npm run social-growth:cron
 */

const base =
  process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ||
  process.env.APP_URL?.replace(/\/$/, "") ||
  "http://localhost:3001";

const secret = process.env.CRON_SECRET?.trim();

async function main() {
  const headers: Record<string, string> = {};
  if (secret) {
    headers.Authorization = `Bearer ${secret}`;
  }

  const res = await fetch(`${base}/api/cron/social-growth`, {
    method: "POST",
    headers,
  });

  const body = await res.text();
  if (!res.ok) {
    console.error("[SOCIAL GROWTH CRON] Failed:", res.status, body);
    process.exit(1);
  }

  console.log("[SOCIAL GROWTH CRON] Complete:", body);
}

main().catch((err) => {
  console.error("[SOCIAL GROWTH CRON] Error:", err);
  process.exit(1);
});
