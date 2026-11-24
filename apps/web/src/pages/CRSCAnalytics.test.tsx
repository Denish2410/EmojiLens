import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { CRSCResult, ExperimentRow } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API responses for UI tests only; not research results.
const exp = { id: 2, name: "pipeline check", status: "completed", config: {}, config_hash: "x", total_items: 1, done_items: 1, failed_items: 0, cancel_requested: false, error: null, created_at: "2026-11-25T00:00:00Z", started_at: null, finished_at: null, uses_test_doubles: true } as ExperimentRow;
const row = (metric: "crsc_sem" | "crsc_safe", stratum: string, value: string, v: number) => ({
  metric, model: "td", stratum, stratum_value: value, value: v, ci_low: v - 0.1, ci_high: Math.min(1, v + 0.1), n: 12, n_groups: 6,
  details: { missing: 0, identity_pairs: 6, identity_failures: 0, unsafe_to_safe: 2, safe_to_unsafe: 1, unknown: 0, flip_rate: 0.25 },
});
const result: CRSCResult = {
  experiment_id: 2, crsc_version: "0.1.0", experimental: true, computed_at: "2026-11-25T01:00:00Z", resamples: 200, seed: 3,
  synthetic_fixture: true, test_double: true, research_reportable: false,
  results: [row("crsc_sem", "overall", "all", 0.81), row("crsc_safe", "overall", "all", 0.75), row("crsc_sem", "language", "en", 0.9), row("crsc_sem", "language", "hi-Latn", 0.7)],
};

describe("CRSC Analytics", () => {
  it("shows an empty state without completed experiments", async () => {
    server.use(http.get("*/api/v1/experiments", () => HttpResponse.json([])));
    renderApp("/crsc");
    expect(await screen.findByTestId("crsc-empty")).toBeInTheDocument();
  });

  it("computes, keeps metrics separate, shows flips and the not-reportable banner", async () => {
    server.use(
      http.get("*/api/v1/experiments", () => HttpResponse.json([exp])),
      http.get("*/api/v1/experiments/2/crsc", () => HttpResponse.json({ ...result, results: [], computed_at: null })),
      http.post("*/api/v1/experiments/2/crsc", () => HttpResponse.json(result)),
    );
    const user = userEvent.setup();
    renderApp("/crsc");
    expect(await screen.findByText(/Not computed yet/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /compute crsc/i }));
    expect(await screen.findByTestId("sem-td")).toHaveTextContent("0.810");
    expect(screen.getByTestId("safe-td")).toHaveTextContent("0.750");
    expect(screen.getByTestId("not-reportable")).toHaveTextContent("synthetic fixture");
    expect(screen.getByText("unsafe→safe").nextElementSibling).toHaveTextContent("2");
    expect(screen.getByRole("table")).toHaveTextContent("hi-Latn");
  });
});
