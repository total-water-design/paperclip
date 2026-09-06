import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const roots: string[] = [];
const installer = path.resolve(import.meta.dirname, "../../../deploy/systemd/paperclip-service-install");

afterEach(() => {
  for (const root of roots.splice(0)) fs.rmSync(root, { recursive: true, force: true });
});

function fixture() {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), "paperclip-shadow-stage-"));
  roots.push(base);
  const root = path.join(base, "root");
  const bin = path.join(base, "bin");
  const archive = path.join(base, "paperclipai.tgz");
  const manifest = path.join(base, "paperclipai.certification.json");
  const supervisorLog = path.join(base, "systemctl.log");
  fs.mkdirSync(root, { mode: 0o700 });
  fs.mkdirSync(bin, { mode: 0o700 });
  fs.writeFileSync(archive, "certified archive fixture\n");
  fs.writeFileSync(manifest, "{}\n");
  fs.writeFileSync(path.join(bin, "visudo"), "#!/bin/sh\nexit 0\n", { mode: 0o700 });
  fs.writeFileSync(path.join(bin, "systemctl"), `#!/bin/sh\nprintf '%s\\n' "$*" >> "${supervisorLog}"\nexit 99\n`, { mode: 0o700 });
  const env = {
    ...process.env,
    PATH: `${bin}:${process.env.PATH}`,
    PAPERCLIP_INSTALL_ROOT: root,
    PAPERCLIP_INSTALL_OWNER: String(process.getuid!()),
    PAPERCLIP_INSTALL_GROUP: String(process.getgid!()),
    PAPERCLIP_CERTIFIED_ARCHIVE_SOURCE: archive,
    PAPERCLIP_CERTIFICATION_MANIFEST_SOURCE: manifest,
  };
  return { base, root, archive, manifest, supervisorLog, env };
}

function stage(input: ReturnType<typeof fixture>, env: NodeJS.ProcessEnv = input.env) {
  return execFileSync("bash", [installer, "stage-preflight"], { env, encoding: "utf8" });
}

describe("systemd shadow staging", () => {
  it("stages and validates the complete artifact set without calling the supervisor", () => {
    const input = fixture();
    expect(stage(input)).toBe("");
    expect(fs.existsSync(path.join(input.root, "etc/systemd/system/paperclip.service"))).toBe(true);
    expect(fs.statSync(path.join(input.root, "etc/paperclip/paperclip.env")).mode & 0o777).toBe(0o640);
    expect(fs.existsSync(input.supervisorLog)).toBe(false);
  });

  it.each([
    ["relative root", (input: ReturnType<typeof fixture>) => ({ ...input.env, PAPERCLIP_INSTALL_ROOT: "relative" }), /absolute, non-root/],
    ["non-canonical root", (input: ReturnType<typeof fixture>) => ({ ...input.env, PAPERCLIP_INSTALL_ROOT: `${input.root}/..\/root` }), /must be canonical/],
    ["wrong owner", (input: ReturnType<typeof fixture>) => ({ ...input.env, PAPERCLIP_INSTALL_OWNER: "99999" }), /unsafe staging root owner/],
    ["unsafe mode", (input: ReturnType<typeof fixture>) => { fs.chmodSync(input.root, 0o755); return input.env; }, /unsafe staging root mode/],
    ["nonempty root", (input: ReturnType<typeof fixture>) => { fs.writeFileSync(path.join(input.root, "occupied"), "x"); return input.env; }, /must be empty/],
  ])("rejects %s before staging", (_name, mutate, message) => {
    const input = fixture();
    const env = mutate(input);
    const before = fs.readdirSync(input.root);
    expect(() => stage(input, env)).toThrow(message);
    expect(fs.readdirSync(input.root)).toEqual(before);
    expect(fs.existsSync(input.supervisorLog)).toBe(false);
  });

  it("rejects symlink traversal", () => {
    const input = fixture();
    const link = path.join(input.base, "linked-root");
    fs.symlinkSync(input.root, link);
    expect(() => stage(input, { ...input.env, PAPERCLIP_INSTALL_ROOT: link })).toThrow(/unsafe staging root|traversal contains a symlink/);
    expect(fs.readdirSync(input.root)).toEqual([]);
  });

  it("normal install validates sources before snapshot or replacement", () => {
    const input = fixture();
    const dropin = path.join(input.root, "etc/systemd/system/paperclip.service.d");
    fs.mkdirSync(dropin, { recursive: true });
    fs.writeFileSync(path.join(dropin, "existing.conf"), "preserve\n");
    const backup = path.join(input.base, "rollback");
    expect(() => execFileSync("bash", [installer, "install"], {
      env: { ...input.env, PAPERCLIP_CERTIFIED_ARCHIVE_SOURCE: path.join(input.base, "missing"), PAPERCLIP_ROLLBACK_ROOT: backup },
      encoding: "utf8",
    })).toThrow(/absolute, regular, non-symlink certified archive/);
    expect(fs.readFileSync(path.join(dropin, "existing.conf"), "utf8")).toBe("preserve\n");
    expect(fs.existsSync(backup)).toBe(false);
    expect(fs.existsSync(input.supervisorLog)).toBe(false);
  });
});
