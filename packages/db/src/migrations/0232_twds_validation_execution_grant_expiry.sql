ALTER TABLE "validation_execution_grants" ADD COLUMN "expires_at" timestamp with time zone;
--> statement-breakpoint
UPDATE "validation_execution_grants" SET "expires_at" = "created_at" + interval '1 hour' WHERE "expires_at" IS NULL;
--> statement-breakpoint
ALTER TABLE "validation_execution_grants" ALTER COLUMN "expires_at" SET NOT NULL;
