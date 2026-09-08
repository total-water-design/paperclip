import { describe, expect, it } from "vitest";
import { resolveCodexModelTransportUrls } from "./model-transport.js";

describe("resolveCodexModelTransportUrls", () => {
  it("uses ChatGPT only for subscription transport", () => {
    expect(resolveCodexModelTransportUrls({}, "subscription")).toEqual(["https://chatgpt.com"]);
  });

  it("uses the OpenAI default for API-key transport", () => {
    expect(resolveCodexModelTransportUrls({}, "api")).toEqual(["https://api.openai.com"]);
  });

  it("uses the configured OpenAI-compatible origin", () => {
    expect(resolveCodexModelTransportUrls({
      OPENAI_BASE_URL: " https://model-gateway.example/v1 ",
    }, "api")).toEqual(["https://model-gateway.example/v1"]);
  });

  it("honors legacy base URL variables without adding the default", () => {
    expect(resolveCodexModelTransportUrls({
      OPENAI_API_BASE_URL: "https://legacy-gateway.example/openai",
    }, "api")).toEqual(["https://legacy-gateway.example/openai"]);
  });
});
