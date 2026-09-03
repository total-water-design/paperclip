#!/usr/bin/env node

import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error(`paperclip runtime wrapper: missing ${name}`);
  return resolve(value);
}
function processStartTime(pid) {
  try { return readFileSync(`/proc/${pid}/stat`, "utf8").split(" ")[21] ?? null; } catch { return null; }
}
function atomicWrite(file, contents) {
  const temporary = `${file}.${process.pid}.${Date.now()}.tmp`;
  writeFileSync(temporary, contents, { mode: 0o600 });
  renameSync(temporary, file);
}
function existingLivePid(pidFile, identityFile) {
  try {
    const pid = Number(readFileSync(pidFile, "utf8").trim());
    const identity = JSON.parse(readFileSync(identityFile, "utf8"));
    return Number.isInteger(pid) && pid > 0 && identity.pid === pid && processStartTime(pid) === identity.processStartTime ? pid : null;
  } catch { return null; }
}

const pidFile = required("PAPERCLIP_RUNTIME_PID_FILE");
const identityFile = required("PAPERCLIP_RUNTIME_IDENTITY");
const artifactIdentity = JSON.parse(readFileSync(required("PAPERCLIP_ARTIFACT_IDENTITY"), "utf8"));
const executable = required("PAPERCLIP_EXECUTABLE");
const active = existingLivePid(pidFile, identityFile);
if (active) throw new Error(`paperclip runtime wrapper: runtime PID ${active} is already active`);
for (const file of [pidFile, identityFile]) { try { unlinkSync(file); } catch (error) { if (error.code !== "ENOENT") throw error; } }

const child = spawn(executable, ["run", "--instance", process.env.PAPERCLIP_INSTANCE_ID], { stdio: "inherit", env: process.env });
child.once("spawn", () => {
  const start = processStartTime(child.pid);
  if (!start) { child.kill("SIGTERM"); throw new Error("paperclip runtime wrapper: cannot read child process identity"); }
  const executableSha256 = createHash("sha256").update(readFileSync(executable)).digest("hex");
  atomicWrite(identityFile, `${JSON.stringify({ pid: child.pid, processStartTime: start, sourceSha: artifactIdentity.source.sha, executableSha256 })}\n`);
  atomicWrite(pidFile, `${child.pid}\n`);
});
for (const signal of ["SIGTERM", "SIGINT", "SIGHUP"]) process.on(signal, () => child.kill(signal));
child.once("error", (error) => { console.error(`paperclip runtime wrapper: ${error.message}`); process.exitCode = 1; });
child.once("exit", (code, signal) => {
  try {
    const pid = Number(readFileSync(pidFile, "utf8").trim());
    const identity = JSON.parse(readFileSync(identityFile, "utf8"));
    if (pid === child.pid && identity.pid === child.pid && identity.processStartTime === processStartTime(child.pid)) {
      unlinkSync(pidFile); unlinkSync(identityFile);
    } else if (pid === child.pid && identity.pid === child.pid) {
      unlinkSync(pidFile); unlinkSync(identityFile);
    }
  } catch {}
  process.exitCode = code ?? (signal ? 1 : 0);
});
