ALTER TABLE "approvals" ADD COLUMN "open_deduplication_key" text;--> statement-breakpoint
ALTER TABLE "approvals" ADD COLUMN "cancellation_reason" text;--> statement-breakpoint
ALTER TABLE "approvals" ADD COLUMN "cancelled_by_agent_id" uuid;--> statement-breakpoint
ALTER TABLE "approvals" ADD COLUMN "cancelled_by_user_id" text;--> statement-breakpoint
ALTER TABLE "approvals" ADD COLUMN "cancelled_at" timestamp with time zone;--> statement-breakpoint
ALTER TABLE "approvals" ADD CONSTRAINT "approvals_cancelled_by_agent_id_agents_id_fk" FOREIGN KEY ("cancelled_by_agent_id") REFERENCES "public"."agents"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "approvals_company_open_deduplication_uq" ON "approvals" USING btree ("company_id","open_deduplication_key") WHERE "approvals"."type" = 'request_board_approval' and "approvals"."status" in ('pending', 'revision_requested') and "approvals"."open_deduplication_key" is not null;
