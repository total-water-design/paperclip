import {
  cpSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const packageJsonPath = fileURLToPath(
  new URL("../../package.json", import.meta.url),
);
const runnerShimPath = fileURLToPath(
  new URL("../vendor/paperclip-runner/index.ts", import.meta.url),
);

describe("server package build script", () => {
  it("builds the compiled package entry during prepack", () => {
    const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8")) as {
      scripts?: Record<string, string>;
    };

    expect(packageJson.scripts?.prepack).toBe(
      "pnpm run prepare:ui-dist && pnpm run build",
    );
  });

  it("copies static runtime asset directories into dist", () => {
    const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8")) as {
      scripts?: Record<string, string>;
    };
    const buildScript = packageJson.scripts?.build ?? "";

    expect(buildScript).toContain(
      "mkdir -p dist/onboarding-assets dist/built-ins",
    );
    expect(buildScript).toContain(
      "cp -R src/onboarding-assets/. dist/onboarding-assets/",
    );
    expect(buildScript).toContain("cp -R src/built-ins/. dist/built-ins/");
  });

  it("keeps the private runner dependency graph closed and vendors its build", () => {
    const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8")) as {
      scripts?: Record<string, string>;
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };

    expect(packageJson.dependencies?.["@paperclipai/paperclip-runner"]).toBe(
      "workspace:*",
    );
    expect(
      packageJson.devDependencies?.["@paperclipai/paperclip-runner"],
    ).toBeUndefined();
    expect(packageJson.scripts?.["prepare:runner-vendor"]).toBe(
      "pnpm --filter @paperclipai/paperclip-runner build",
    );
    expect(packageJson.scripts?.build).toContain(
      "cp -R ../packages/paperclip-runner/dist/. dist/vendor/paperclip-runner/",
    );
  });

  it("loads the runner through its dependency-owning package boundary", () => {
    const shim = readFileSync(runnerShimPath, "utf8");

    expect(shim).toContain(
      'import("@paperclipai/paperclip-runner")',
    );
    expect(shim).not.toContain(
      '"../../../../packages/paperclip-runner/src/index.ts"',
    );
  });

  it("resolves the runner from a detached server dependency graph", () => {
    const root = mkdtempSync(join(tmpdir(), "paperclip-runner-closure-"));
    const detachedShim = join(
      root,
      "server/src/vendor/paperclip-runner/index.ts",
    );
    const detachedRunner = join(
      root,
      "server/node_modules/@paperclipai/paperclip-runner",
    );
    const runnerRoot = fileURLToPath(
      new URL("../../../packages/paperclip-runner/", import.meta.url),
    );

    mkdirSync(dirname(detachedShim), { recursive: true });
    mkdirSync(dirname(detachedRunner), { recursive: true });
    writeFileSync(
      join(root, "server/package.json"),
      JSON.stringify({ type: "module" }),
    );
    cpSync(runnerShimPath, detachedShim);
    cpSync(join(runnerRoot, "src"), join(detachedRunner, "src"), { recursive: true });
    symlinkSync(
      join(runnerRoot, "node_modules"),
      join(detachedRunner, "node_modules"),
      "dir",
    );
    writeFileSync(
      join(detachedRunner, "package.json"),
      JSON.stringify({
        name: "@paperclipai/paperclip-runner",
        type: "module",
        exports: { ".": "./src/index.ts" },
      }),
    );

    try {
      const result = spawnSync(
        process.execPath,
        ["--import", import.meta.resolve("tsx"), detachedShim],
        {
          cwd: join(root, "server"),
          encoding: "utf8",
        },
      );

      expect(result.stderr).toBe("");
      expect(result.status).toBe(0);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
