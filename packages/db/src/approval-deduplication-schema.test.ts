import fs from "node:fs";
import { getTableConfig } from "drizzle-orm/pg-core";
import { describe, expect, it } from "vitest";
import { approvals } from "./schema/approvals.js";

const INDEX_NAME = "approvals_company_open_deduplication_uq";

describe("approval deduplication schema", () => {
  it("keeps rolling-compatible nullable identity and cancellation fields", () => {
    const columns = getTableConfig(approvals).columns;
    for (const name of [
      "open_deduplication_key",
      "cancellation_reason",
      "cancelled_by_agent_id",
      "cancelled_by_user_id",
      "cancelled_at",
    ]) {
      expect(columns.find((column) => column.name === name)?.notNull).toBe(false);
    }
  });

  it("enforces one company-scoped keyed open Board approval", () => {
    const index = getTableConfig(approvals).indexes.find((candidate) => candidate.config.name === INDEX_NAME);
    expect(index?.config.unique).toBe(true);
    expect(index?.config.columns.map((column) => (column as { name: string }).name))
      .toEqual(["company_id", "open_deduplication_key"]);
    expect(index?.config.where).toBeDefined();
  });

  it("ships an additive migration without backfill or fixture mutation", () => {
    const sql = fs.readFileSync(
      new URL("./migrations/0234_approval_open_deduplication.sql", import.meta.url),
      "utf8",
    );
    expect(sql).toContain(`CREATE UNIQUE INDEX "${INDEX_NAME}"`);
    expect(sql).toContain("'pending', 'revision_requested'");
    expect(sql).not.toMatch(/^\s*(?:UPDATE|DELETE|DROP)\b/im);
    for (const fixtureId of [
      "544365d1-e653-4c55-a290-fca919ffbf1f",
      "d93fefee-488a-4d93-a43a-7199d88d0ab9",
      "eb43b4e8-65c0-4cc8-b2c6-917ccf71c1fc",
    ]) {
      expect(sql).not.toContain(fixtureId);
    }
  });
});
