import { describe, expect, it } from "vitest";

import { resolveBuildCommit } from "../../scripts/write-build-stamp.mjs";

describe("resolveBuildCommit", () => {
  it("prefers the git commit over the supplied environment commit", () => {
    expect(
      resolveBuildCommit(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      ),
    ).toBe("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
  });

  it("falls back to PAPERCLIP_BUILD_COMMIT when git gives no commit", () => {
    // A Docker image build excludes `.git`, so the git lookup returns null. The
    // image build passes the commit in the environment instead.
    expect(resolveBuildCommit(null, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))
      .toBe("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
  });

  it("trims the supplied commit", () => {
    expect(resolveBuildCommit(null, "  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB\n"))
      .toBe("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
  });

  it("returns null when neither git nor the environment gives a commit", () => {
    expect(resolveBuildCommit(null, undefined)).toBe(null);
  });

  it("treats an empty supplied commit as absent", () => {
    expect(resolveBuildCommit(null, "")).toBe(null);
    expect(resolveBuildCommit(null, "   ")).toBe(null);
  });

  it("rejects truncated source identifiers", () => {
    expect(resolveBuildCommit("aaaaaaa", "bbbbbbb")).toBeNull();
  });
});
