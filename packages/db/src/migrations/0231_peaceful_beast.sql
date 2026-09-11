CREATE TABLE "semantic_action_receipts" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"company_id" uuid NOT NULL,
	"scope" text NOT NULL,
	"operation_id" text NOT NULL,
	"input_digest" text NOT NULL,
	"outcome" jsonb,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "semantic_action_receipts" ADD CONSTRAINT "semantic_action_receipts_company_id_companies_id_fk" FOREIGN KEY ("company_id") REFERENCES "public"."companies"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "semantic_action_receipts_company_scope_uq" ON "semantic_action_receipts" USING btree ("company_id","scope");