ALTER TABLE "approvals" ADD COLUMN "restriction_action_key" text;--> statement-breakpoint
CREATE INDEX "approvals_company_restriction_action_key_idx" ON "approvals" USING btree ("company_id","restriction_action_key") WHERE "approvals"."restriction_action_key" is not null;
--> statement-breakpoint
UPDATE "approvals"
SET "restriction_action_key" = concat_ws(E'\n',
  nullif(btrim(regexp_replace(regexp_replace(lower(coalesce("payload"->>'action', '')), '[^a-z0-9:_./-]+', ' ', 'g'), '\\s+', ' ', 'g')), ''),
  nullif(btrim(regexp_replace(regexp_replace(lower(coalesce("payload"->>'recommendedAction', '')), '[^a-z0-9:_./-]+', ' ', 'g'), '\\s+', ' ', 'g')), ''),
  nullif(btrim(regexp_replace(regexp_replace(lower(coalesce("payload"->>'title', '')), '[^a-z0-9:_./-]+', ' ', 'g'), '\\s+', ' ', 'g')), ''),
  nullif(btrim(regexp_replace(regexp_replace(lower(coalesce("payload"->>'scope', '')), '[^a-z0-9:_./-]+', ' ', 'g'), '\\s+', ' ', 'g')), ''),
  nullif(btrim(regexp_replace(regexp_replace(lower(coalesce("payload"->>'target', '')), '[^a-z0-9:_./-]+', ' ', 'g'), '\\s+', ' ', 'g')), ''),
  nullif(btrim(regexp_replace(regexp_replace(lower(coalesce("payload"->>'environment', '')), '[^a-z0-9:_./-]+', ' ', 'g'), '\\s+', ' ', 'g')), '')
)
WHERE "restriction_action_key" IS NULL;
