const OPENAI_BASE_URL_KEYS = ["OPENAI_BASE_URL", "OPENAI_API_BASE", "OPENAI_API_BASE_URL"] as const;

function nonEmptyEnvValue(env: Record<string, string>, key: string): string | null {
  const value = env[key];
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}

/** Resolve Codex-owned model transport independently of candidate target egress. */
export function resolveCodexModelTransportUrls(
  env: Record<string, string>,
  billingType: "api" | "subscription",
): string[] {
  if (billingType === "subscription") return ["https://chatgpt.com"];

  for (const key of OPENAI_BASE_URL_KEYS) {
    const configured = nonEmptyEnvValue(env, key);
    if (configured) return [configured];
  }
  return ["https://api.openai.com"];
}
