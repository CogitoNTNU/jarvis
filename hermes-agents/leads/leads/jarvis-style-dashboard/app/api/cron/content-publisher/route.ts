import { NextResponse } from "next/server";
import { runContentPublisher } from "@/lib/content-publisher";

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
  const result = await runContentPublisher();
  return NextResponse.json({ ok: true, ...result });
}

export async function GET(req: Request) {
  if (!authorized(req)) {
    return NextResponse.json({
      ok: true,
      endpoint: "/api/cron/content-publisher",
      description: "POST with Authorization: Bearer CRON_SECRET to publish approved content.",
    });
  }
  const result = await runContentPublisher();
  return NextResponse.json({ ok: true, ...result });
}
