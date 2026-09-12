import { describe, expect, it } from "vitest";
import { chromiumLaunchOptions } from "../../../tests/playwright-shared.js";

describe("chromiumLaunchOptions", () => {
  it("uses the narrow agent-sandbox workaround required by TOT-3626", () => {
    expect(chromiumLaunchOptions).toEqual({
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    });
  });
});
