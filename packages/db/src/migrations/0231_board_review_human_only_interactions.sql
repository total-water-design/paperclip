-- Pending human-only interactions are Board review paths. Repair historical
-- rows that predate the atomic create-time routing rule, without touching
-- resolved/expired cards or terminal issues.
UPDATE "issues" AS issue
SET
  "status" = 'in_review',
  "status_version" = issue."status_version" + 1,
  "updated_at" = NOW()
WHERE issue."status" IN ('blocked', 'in_progress')
  AND EXISTS (
    SELECT 1
    FROM "issue_thread_interactions" AS interaction
    WHERE interaction."company_id" = issue."company_id"
      AND interaction."issue_id" = issue."id"
      AND interaction."status" = 'pending'
      AND interaction."effective_resolver_policy" = 'human_only'
  );
