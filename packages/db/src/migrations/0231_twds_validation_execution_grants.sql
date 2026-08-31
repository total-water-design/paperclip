CREATE TABLE "validation_execution_grants" ("id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,"company_id" uuid NOT NULL,"approval_issue_id" uuid NOT NULL,"approval_interaction_id" uuid NOT NULL,"approval_comment_id" uuid NOT NULL,"approval_source_run_id" uuid,"successor_run_id" uuid,"consumer_run_id" uuid,"issue_id" uuid NOT NULL,"candidate_sha" text NOT NULL,"contract_sha" text NOT NULL,"oracle_sha" text NOT NULL,"capability" text DEFAULT 'validation_execution' NOT NULL,"status" text DEFAULT 'issued' NOT NULL,"created_at" timestamp with time zone DEFAULT now() NOT NULL,"consumed_at" timestamp with time zone,"invalidated_at" timestamp with time zone,"invalidation_reason" text,CONSTRAINT "validation_execution_grants_capability_check" CHECK ("capability" = 'validation_execution'),CONSTRAINT "validation_execution_grants_status_check" CHECK ("status" IN ('issued','consumed','invalidated')));
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_company_fk" FOREIGN KEY ("company_id") REFERENCES "public"."companies"("id") ON DELETE cascade;
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_approval_issue_fk" FOREIGN KEY ("approval_issue_id") REFERENCES "public"."issues"("id");
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_approval_interaction_fk" FOREIGN KEY ("approval_interaction_id") REFERENCES "public"."issue_thread_interactions"("id");
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_approval_comment_fk" FOREIGN KEY ("approval_comment_id") REFERENCES "public"."issue_comments"("id");
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_source_run_fk" FOREIGN KEY ("approval_source_run_id") REFERENCES "public"."heartbeat_runs"("id") ON DELETE set null;
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_successor_run_fk" FOREIGN KEY ("successor_run_id") REFERENCES "public"."heartbeat_runs"("id") ON DELETE set null;
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_consumer_run_fk" FOREIGN KEY ("consumer_run_id") REFERENCES "public"."heartbeat_runs"("id") ON DELETE set null;
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ADD CONSTRAINT "validation_execution_grants_issue_fk" FOREIGN KEY ("issue_id") REFERENCES "public"."issues"("id");
--> statement-breakpoint
CREATE UNIQUE INDEX "validation_execution_grants_approval_interaction_uq" ON "validation_execution_grants" ("approval_interaction_id");
--> statement-breakpoint
CREATE UNIQUE INDEX "validation_execution_grants_successor_run_uq" ON "validation_execution_grants" ("successor_run_id") WHERE "successor_run_id" IS NOT NULL;
--> statement-breakpoint
CREATE UNIQUE INDEX "validation_execution_grants_consumer_run_uq" ON "validation_execution_grants" ("consumer_run_id") WHERE "consumer_run_id" IS NOT NULL;
--> statement-breakpoint
CREATE INDEX "validation_execution_grants_issued_issue_idx" ON "validation_execution_grants" ("company_id","issue_id","status");
