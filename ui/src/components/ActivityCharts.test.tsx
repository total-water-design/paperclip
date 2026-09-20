// @vitest-environment jsdom

import type { ReactNode } from "react";
import { flushSync } from "react-dom";
import { createRoot, type Root } from "react-dom/client";
import type { HeartbeatRun } from "@paperclipai/shared";
import type { HeartbeatRunStats } from "../api/heartbeats";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getLast14Days, RunActivityChart, SuccessRateChart } from "./ActivityCharts";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-04-20T12:00:00.000Z"));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  flushSync(() => root.unmount());
  container.remove();
  vi.useRealTimers();
});

function render(ui: ReactNode) {
  flushSync(() => {
    root.render(ui);
  });
}

function createRun(overrides: Partial<HeartbeatRun> = {}): HeartbeatRun {
  return {
    id: "run-1",
    companyId: "company-1",
    agentId: "agent-1",
    responsibleUserId: null,
    invocationSource: "on_demand",
    triggerDetail: "manual",
    status: "succeeded",
    startedAt: new Date("2026-04-20T11:58:00.000Z"),
    finishedAt: new Date("2026-04-20T11:59:00.000Z"),
    error: null,
    wakeupRequestId: null,
    exitCode: 0,
    signal: null,
    usageJson: null,
    resultJson: null,
    sessionIdBefore: null,
    sessionIdAfter: null,
    logStore: null,
    logRef: null,
    logBytes: null,
    logSha256: null,
    logCompressed: false,
    lastOutputAt: null,
    lastOutputSeq: 0,
    lastOutputStream: null,
    lastOutputBytes: null,
    stdoutExcerpt: null,
    stderrExcerpt: null,
    errorCode: null,
    externalRunId: null,
    processPid: null,
    processGroupId: null,
    processStartedAt: null,
    retryOfRunId: null,
    processLossRetryCount: 0,
    scheduledRetryAt: null,
    scheduledRetryAttempt: 0,
    scheduledRetryReason: null,
    livenessState: null,
    livenessReason: null,
    continuationAttempt: 0,
    lastUsefulActionAt: null,
    nextAction: null,
    contextSnapshot: null,
    createdAt: new Date("2026-04-20T11:58:00.000Z"),
    updatedAt: new Date("2026-04-20T11:59:00.000Z"),
    ...overrides,
  };
}

describe("ActivityCharts", () => {
  it("renders empty run charts when dashboard aggregate data is temporarily missing", () => {
    render(<RunActivityChart activity={undefined} />);
    expect(container.textContent).toContain("No runs yet");

    render(<SuccessRateChart activity={undefined} />);
    expect(container.textContent).toContain("No runs yet");
  });

  it("still aggregates raw agent runs for detail charts", () => {
    render(
      <RunActivityChart
        runs={[
          createRun({ id: "run-success", status: "succeeded" }),
          createRun({ id: "run-failed", status: "failed", errorCode: "provider_quota" }),
        ]}
      />,
    );

    expect(container.textContent).not.toContain("No runs yet");
    // Tooltip now carries the per-day breakdown (incl. failure error codes).
    const dayCell = container.querySelector("[title^='2026-04-20: 2 runs']");
    expect(dayCell).not.toBeNull();
    expect(dayCell?.getAttribute("title")).toContain("provider_quota: 1");
  });

  it("renders a distinct recovered segment and legend for recovered restart kills", () => {
    render(
      <RunActivityChart
        activity={[
          {
            date: "2026-04-20",
            succeeded: 3,
            failed: 1,
            recovered: 4,
            other: 0,
            total: 8,
            failedByErrorCode: { process_lost: 1 },
          },
        ]}
      />,
    );

    expect(container.textContent).toContain("Recovered");
    const dayCell = container.querySelector("[title*='recovered: 4']");
    expect(dayCell).not.toBeNull();
  });
  describe("stats prop path", () => {
    function chartDays() {
      const days = getLast14Days();
      return { today: days[13]!, yesterday: days[12]!, twoDaysAgo: days[11]!, fiveDaysAgo: days[8]! };
    }
    function hasTitle(prefix: string) {
      return Array.from(container.querySelectorAll("[title]")).some((element) =>
        element.getAttribute("title")?.startsWith(prefix),
      );
    }
    function hasTitleText(text: string) {
      return Array.from(container.querySelectorAll("[title]")).some((element) =>
        element.getAttribute("title")?.includes(text),
      );
    }
    function makeStats(overrides: Partial<HeartbeatRunStats>[]): HeartbeatRunStats[] {
      return overrides.map((o) => ({ date: chartDays().today, status: "succeeded", count: 1, ...o }));
    }

    it("RunActivityChart renders stats across two UTC days", () => {
      const { today, yesterday } = chartDays();
      const stats = makeStats([
        { date: yesterday, status: "succeeded", count: 3 },
        { date: yesterday, status: "failed", count: 1 },
        { date: today, status: "succeeded", count: 2 },
        { date: today, status: "timed_out", count: 1 },
        { date: today, status: "other", count: 5 },
      ]);

      render(<RunActivityChart stats={stats} />);

      expect(container.textContent).not.toContain("No runs yet");
      // Apr 19 total = 4 runs, Apr 20 total = 8 runs
      expect(hasTitle(`${yesterday}: 4 runs`)).toBe(true);
      expect(hasTitle(`${today}: 8 runs`)).toBe(true);
    });

    it("SuccessRateChart renders stats and shows correct success ratio tooltip", () => {
      const { twoDaysAgo } = chartDays();
      const stats = makeStats([
        { date: twoDaysAgo, status: "succeeded", count: 8 },
        { date: twoDaysAgo, status: "failed", count: 2 },
      ]);

      render(<SuccessRateChart stats={stats} />);

      expect(container.textContent).not.toContain("No runs yet");
      // 8/10 = 80% success
      expect(hasTitleText("80% (8/10)")).toBe(true);
    });

    it("drops rows outside the 14-day window", () => {
      const stats = makeStats([
        // Too old — not in window
        { date: "2026-03-01", status: "succeeded", count: 99 },
        // In window
        { date: "2026-04-20", status: "succeeded", count: 1 },
      ]);

      render(<RunActivityChart stats={stats} />);

      expect(hasTitle("2026-03-01: 99 runs")).toBe(false);
      expect(container.textContent).not.toContain("No runs yet");
    });

    it("dedupes succeeded and failed+timed_out into correct buckets", () => {
      const { fiveDaysAgo } = chartDays();
      const stats = makeStats([
        { date: fiveDaysAgo, status: "succeeded", count: 4 },
        { date: fiveDaysAgo, status: "failed", count: 1 },
        { date: fiveDaysAgo, status: "timed_out", count: 2 },
        { date: fiveDaysAgo, status: "other", count: 3 },
      ]);

      render(<RunActivityChart stats={stats} />);

      // total = 4+1+2+3 = 10
      expect(hasTitle(`${fiveDaysAgo}: 10 runs`)).toBe(true);
    });
  });

});
