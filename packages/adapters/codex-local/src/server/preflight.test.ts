import { describe, expect, it } from "vitest";
import { classifyCodexPreflightFailure } from "./test.js";

describe("classifyCodexPreflightFailure", () => {
  it("fast-fails authentication and CONNECT policy failures", () => {
    expect(classifyCodexPreflightFailure("authentication required; please run codex login")).toBe("auth");
    expect(classifyCodexPreflightFailure("proxy returned HTTP CONNECT 403 Forbidden")).toBe("policy");
    expect(classifyCodexPreflightFailure("api.openai.com is not allowlisted")).toBe("policy");
  });

  it("only marks retryable transport failures as transient", () => {
    expect(classifyCodexPreflightFailure("Reconnecting: error sending request")).toBe("transient");
    expect(classifyCodexPreflightFailure("503 Service Unavailable")).toBe("transient");
    expect(classifyCodexPreflightFailure("model is not supported")).toBe("fatal");
  });
});
