import { NextResponse } from "next/server";
import { runSocialGrowthWorker } from "@/lib/social-growth-worker";

export const dynamic = "force-dynamic";

function authorized(req: Request): boolean {
  const secret = process.env.CRON_SECRET?.trim();
  if (!secret) return process.env.NODE_ENV !== "production";
  const header = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  return header === secret;
}

export async function POST(req: Request) {
  if (!authorized(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const result = await runSocialGrowthWorker();
  return NextResponse.json({ ok: true, ...result });
}

export async function GET(req: Request) {
  if (!authorized(req)) {
    return NextResponse.json({
      ok: true,
      endpoint: "/api/cron/social-growth",
      description:
        "POST with Authorization: Bearer CRON_SECRET to run social growth automation (greetings, follows, likes, comments).",
    });
  }
  const result = await runSocialGrowthWorker();
  return NextResponse.json({ ok: true, ...result });
}
