/**
 * Autonomous content publisher worker (run via cron).
 *
 * Example crontab (every 30 minutes):
 * */30 * * * * cd /path/to/jarvis-style-dashboard && CRON_SECRET=xxx npm run content-publisher:cron
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

  const res = await fetch(`${base}/api/cron/content-publisher`, {
    method: "POST",
    headers,
  });

  const body = await res.text();
  if (!res.ok) {
    console.error("[CONTENT PUBLISHER CRON] Failed:", res.status, body);
    process.exit(1);
  }

  console.log("[CONTENT PUBLISHER CRON] Complete:", body);
}

main().catch((err) => {
  console.error("[CONTENT PUBLISHER CRON] Error:", err);
  process.exit(1);
});
