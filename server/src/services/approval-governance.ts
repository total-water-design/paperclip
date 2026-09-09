import { createHash } from "node:crypto";

export const BOARD_APPROVAL_REASON_CODES = [
  "DEPLOYMENT",
  "PROTECTED_REFERENCE_MUTATION",
  "IRREVERSIBLE_ACTION",
  "MATERIAL_SECURITY_OR_ACCESS_POLICY",
  "EXTERNALLY_CONSEQUENTIAL_ACTION",
  "UNRESOLVED_COS_EXCEPTION",
] as const;

export type BoardApprovalReasonCode = (typeof BOARD_APPROVAL_REASON_CODES)[number];

export type BoardApprovalGovernanceDecision =
  | { outcome: "board_gate"; reasonCode: BoardApprovalReasonCode; source: "explicit" | "inferred" }
  | { outcome: "delegated"; reasonCode: "ROUTINE_DELEGATED_ACTION"; source: "inferred" }
  | { outcome: "route_to_cos"; reasonCode: "COS_REVIEW_REQUIRED"; source: "inferred" };

const BOARD_REASON_SET = new Set<string>(BOARD_APPROVAL_REASON_CODES);

const ROUTINE_ACTION_RE = /\b(?:read[ -]?only|diagnostic|evidence[ -]collection|smoke[ -]test|smoke probe|ci inspection|check inspection|topology|workspace(?: state)?|host[ -]state|integrity check|artifact retrieval|log inspection|test execution)\b/i;

const BOARD_GATE_PATTERNS: ReadonlyArray<{
  reasonCode: Exclude<BoardApprovalReasonCode, "UNRESOLVED_COS_EXCEPTION">;
  pattern: RegExp;
}> = [
  {
    reasonCode: "PROTECTED_REFERENCE_MUTATION",
    pattern: /\b(?:merge|push|force[ -]?push|promote|mutate|update|change|rewrite)\w*\b.{0,100}\b(?:protected (?:branch|ref|reference)|alpha branch|main branch|master branch|release[ -]pin)\b|\b(?:protected (?:branch|ref|reference)|alpha branch|main branch|master branch|release[ -]pin)\b.{0,100}\b(?:merge|push|promote|mutate|update|change|rewrite)\w*\b/i,
  },
  {
    reasonCode: "IRREVERSIBLE_ACTION",
    pattern: /\b(?:destructive|irreversible|drop (?:table|database)|truncate (?:table|data)|delete (?:persistent|production|customer) data|production data migration|migration without (?:safe )?(?:rollback|recovery))\b/i,
  },
  {
    reasonCode: "DEPLOYMENT",
    pattern: /\b(?:activate|activation|deploy|deployment|restart|promote|promotion|release)\w*\b.{0,100}\b(?:live service|running service|production|prod|alpha|staging|shared service|live state)\b|\b(?:production|prod|alpha|staging|shared|live)\b.{0,100}\b(?:activate|activation|deploy|deployment|restart|promotion|release)\w*\b/i,
  },
  {
    reasonCode: "MATERIAL_SECURITY_OR_ACCESS_POLICY",
    pattern: /\b(?:authorize|approve|create|grant|expand|elevate|change|rotate|bind|provision|install)\w*\b.{0,100}\b(?:root|iam|credential|secret|access policy|permission|privilege|firewall|network exposure|egress|branch protection|agents:create|security exception)\b|\bmaterial (?:security|privacy) exception\b/i,
  },
  {
    reasonCode: "EXTERNALLY_CONSEQUENTIAL_ACTION",
    pattern: /\b(?:paid service|purchase|unbudgeted spend|hosting spend|pricing decision|commercial commitment|legal commitment|customer promise|public statement|external contact)\b/i,
  },
];

const EXACT_IDENTITY_KEYS = [
  "authorizationKey",
  "idempotencyKey",
  "requestKey",
  "actionKey",
  "scopeKey",
] as const;

const IMMUTABLE_IDENTITY_KEYS = [
  "sha",
  "candidateSha",
  "headSha",
  "commitSha",
  "artifactDigest",
  "artifactSha256",
] as const;

const STRUCTURED_IDENTITY_KEYS = [
  "action",
  "scope",
  "target",
  "environment",
  "sha",
  "candidateSha",
  "headSha",
  "commitSha",
  "artifactDigest",
  "artifactSha256",
] as const;

function normalizedText(value: unknown): string {
  return typeof value === "string"
    ? value.trim().toLowerCase().replace(/[^a-z0-9:_./-]+/g, " ").replace(/\s+/g, " ")
    : "";
}

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, child]) => [key, stableValue(child)]),
  );
}

function payloadText(payload: Record<string, unknown>): string {
  const values: string[] = [];
  const visit = (value: unknown) => {
    if (typeof value === "string") values.push(value);
    else if (Array.isArray(value)) value.forEach(visit);
    else if (value && typeof value === "object") Object.values(value as Record<string, unknown>).forEach(visit);
  };
  visit(payload);
  return values.join("\n");
}

function proposedActionText(payload: Record<string, unknown>): string {
  return [payload.title, payload.recommendedAction, payload.action]
    .map((value) => typeof value === "string" ? value : "")
    .filter(Boolean)
    .join("\n");
}

export function classifyBoardApprovalRequest(
  payload: Record<string, unknown>,
): BoardApprovalGovernanceDecision {
  const explicitReason = typeof payload.governanceReason === "string"
    ? payload.governanceReason.trim().toUpperCase()
    : null;
  if (explicitReason && BOARD_REASON_SET.has(explicitReason)) {
    return {
      outcome: "board_gate",
      reasonCode: explicitReason as BoardApprovalReasonCode,
      source: "explicit",
    };
  }

  const actionText = proposedActionText(payload);
  for (const gate of BOARD_GATE_PATTERNS) {
    if (gate.pattern.test(actionText)) {
      return { outcome: "board_gate", reasonCode: gate.reasonCode, source: "inferred" };
    }
  }

  const allPayloadText = payloadText(payload);
  for (const gate of BOARD_GATE_PATTERNS) {
    if (gate.pattern.test(allPayloadText)) {
      return { outcome: "route_to_cos", reasonCode: "COS_REVIEW_REQUIRED", source: "inferred" };
    }
  }

  if (ROUTINE_ACTION_RE.test(allPayloadText)) {
    return { outcome: "delegated", reasonCode: "ROUTINE_DELEGATED_ACTION", source: "inferred" };
  }

  return { outcome: "route_to_cos", reasonCode: "COS_REVIEW_REQUIRED", source: "inferred" };
}

export function boardApprovalRequestIdentity(input: {
  type: string;
  payload: Record<string, unknown>;
  issueIds: string[];
}) {
  const explicitIdentity = Object.fromEntries(
    EXACT_IDENTITY_KEYS
      .filter((key) => input.payload[key] !== undefined)
      .map((key) => [key, stableValue(input.payload[key])]),
  );
  const structuredIdentity = Object.fromEntries(
    STRUCTURED_IDENTITY_KEYS
      .filter((key) => input.payload[key] !== undefined)
      .map((key) => [key, stableValue(input.payload[key])]),
  );
  const digests = Array.from(new Set(
    payloadText(input.payload).match(/\b[0-9a-f]{7,64}\b/gi)?.map((value) => value.toLowerCase()) ?? [],
  )).sort();
  const hasAction = normalizedText(input.payload.action).length > 0;
  const hasBoundedScope = [input.payload.scope, input.payload.target, input.payload.environment]
    .some((value) => {
      if (typeof value === "string") return value.trim().length > 0;
      if (Array.isArray(value)) return value.length > 0;
      return Boolean(value && typeof value === "object" && Object.keys(value).length > 0);
    });
  const hasImmutableIdentity = IMMUTABLE_IDENTITY_KEYS.some((key) => {
    const value = input.payload[key];
    return typeof value === "string" && /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/i.test(value.trim());
  });
  const exactIdentityEstablished = hasAction && hasBoundedScope && hasImmutableIdentity;
  const identityPayload = exactIdentityEstablished
    ? { structuredIdentity }
    : { explicitIdentity, structuredIdentity, digests };
  const canonical = JSON.stringify(stableValue({
    version: 1,
    type: input.type,
    title: normalizedText(input.payload.title),
    recommendedAction: normalizedText(input.payload.recommendedAction),
    issueIds: Array.from(new Set(input.issueIds)).sort(),
    ...identityPayload,
  }));

  return {
    fingerprint: createHash("sha256").update(canonical).digest("hex"),
    exactIdentityEstablished,
  };
}
