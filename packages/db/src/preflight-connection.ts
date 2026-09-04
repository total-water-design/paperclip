import { sql } from "drizzle-orm";
import { createDb } from "./client.js";

const databaseUrl = process.env.DATABASE_URL?.trim();
if (!databaseUrl) throw new Error("DATABASE_URL is required");

const db = createDb(databaseUrl);
try {
  const result = await db.execute(sql`
    SELECT
      current_user AS "user",
      current_database() AS "database",
      current_setting('transaction_read_only') AS "transactionReadOnly"
  `);
  const row = result[0];
  process.stdout.write(`${JSON.stringify({ status: "connected", ...row })}\n`);
} finally {
  await db.$client.end({ timeout: 1 });
}
