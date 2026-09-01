CREATE TABLE "managed_secret_capability_grants" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "company_id" uuid NOT NULL REFERENCES "companies"("id") ON DELETE cascade,
  "binding_id" uuid NOT NULL REFERENCES "company_secret_bindings"("id") ON DELETE cascade,
  "agent_id" uuid NOT NULL REFERENCES "agents"("id") ON DELETE cascade,
  "issue_id" uuid REFERENCES "issues"("id") ON DELETE cascade,
  "run_id" uuid REFERENCES "heartbeat_runs"("id") ON DELETE cascade,
  "status" text DEFAULT 'active' NOT NULL,
  "expires_at" timestamp with time zone NOT NULL,
  "created_by_user_id" text,
  "revoked_by_user_id" text,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "revoked_at" timestamp with time zone,
  "revocation_reason" text,
  CONSTRAINT "managed_secret_capability_grants_scope_check" CHECK (("issue_id" IS NOT NULL) <> ("run_id" IS NOT NULL)),
  CONSTRAINT "managed_secret_capability_grants_status_check" CHECK ("status" IN ('active','revoked'))
);
--> statement-breakpoint
CREATE INDEX "managed_secret_capability_grants_scope_idx" ON "managed_secret_capability_grants" ("company_id","agent_id","issue_id","run_id","status");
--> statement-breakpoint
CREATE INDEX "managed_secret_capability_grants_binding_idx" ON "managed_secret_capability_grants" ("binding_id");
