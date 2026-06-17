import "server-only";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { writeFileSync, unlinkSync } from "node:fs";

export type SocialRunnerAction =
  | "scan"
  | "classify-dms"
  | "follow-back"
  | "send-dm"
  | "follow-user"
  | "like-user"
  | "comment-user";

const JARVIS_ROOT =
  process.env.JARVIS_ROOT?.trim() || resolve(process.cwd(), "../../../..");
const RUNNER_PATH = resolve(JARVIS_ROOT, "modules/phillip_spearman_tattoo/engagement_runner.ts");

interface BaseRunnerResult {
  posted?: boolean;
  notes?: string[];
}

export interface SocialRunnerOutput extends BaseRunnerResult {
  comments?: Array<{ author?: string; text?: string; post_ref?: string }>;
  dms?: Array<{ sender?: string; preview?: string; bucket?: string }>;
  follow_backs?: Array<{ username?: string; reason?: string }>;
}

export async function runSocialRunner(params: {
  action: SocialRunnerAction;
  payload?: Record<string, unknown>;
  execute?: boolean;
  verbose?: boolean;
}): Promise<SocialRunnerOutput> {
  const execute = Boolean(params.execute);
  const verbose = Boolean(params.verbose);
  const args = [
    "tsx",
    RUNNER_PATH,
    `--action=${params.action}`,
    "--platform=instagram",
  ];
  if (execute) args.push("--execute");
  if (verbose) args.push("--verbose");

  let payloadPath: string | null = null;
  if (params.payload) {
    payloadPath = join(tmpdir(), `social_runner_${randomUUID()}.json`);
    writeFileSync(payloadPath, JSON.stringify(params.payload), "utf-8");
    args.push(`--payload=${payloadPath}`);
  }

  return new Promise((resolvePromise, rejectPromise) => {
    const proc = spawn("npx", args, {
      cwd: JARVIS_ROOT,
      env: { ...process.env },
    });

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    proc.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    proc.on("close", (code) => {
      if (payloadPath) {
        try {
          unlinkSync(payloadPath);
        } catch {
          // ignore payload cleanup errors
        }
      }
      if (code !== 0) {
        rejectPromise(
          new Error(stderr.trim() || stdout.trim() || `engagement runner exited ${code}`),
        );
        return;
      }
      const body = stdout.trim();
      if (!body) {
        resolvePromise({});
        return;
      }
      try {
        resolvePromise(JSON.parse(body) as SocialRunnerOutput);
      } catch {
        resolvePromise({ notes: [body] });
      }
    });
  });
}
