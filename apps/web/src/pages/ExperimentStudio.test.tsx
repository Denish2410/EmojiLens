import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { ExperimentRow } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API responses for UI tests only.
const exp: ExperimentRow = {
  id: 4, name: "run a", status: "interrupted", config: { model_keys: ["td"] }, config_hash: "f".repeat(64),
  total_items: 10, done_items: 4, failed_items: 1, cancel_requested: false,
  error: "The API stopped while this experiment was running. Stored outputs are kept; resume to continue.",
  created_at: "2026-11-25T00:00:00Z", started_at: null, finished_at: null, uses_test_doubles: true,
};

function base(list: ExperimentRow[]) {
  server.use(
    http.get("*/api/v1/datasets", () => HttpResponse.json([])),
    http.get("*/api/v1/models", () => HttpResponse.json({ device: "cpu", device_reason: "", resources: { available_ram_gb: null, free_disk_gb: 1, cache_dir: "" }, models: [] })),
    http.get("*/api/v1/experiments", () => HttpResponse.json(list)),
    http.get("*/api/v1/experiments/4", () => HttpResponse.json(exp)),
    http.get("*/api/v1/experiments/4/outputs", () => HttpResponse.json({ total: 0, page: 1, page_size: 25, items: [] })),
  );
}

describe("Experiment Studio", () => {
  it("shows empty states when there are no experiments or installed models", async () => {
    base([]);
    renderApp("/experiments");
    expect(await screen.findByTestId("no-experiments")).toBeInTheDocument();
    expect(await screen.findByTestId("no-available-models")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /queue experiment/i })).toBeDisabled();
    expect(screen.getByLabelText(/SafetyJudge label map/)).toBeDisabled();
    expect(screen.getByTestId("labelmap-help")).toHaveTextContent("never mapped to safe/unsafe");
  });

  it("shows interrupted runs explicitly and resumes them", async () => {
    base([exp]);
    let resumed = false;
    server.use(http.post("*/api/v1/experiments/4/resume", () => { resumed = true; return HttpResponse.json({ ...exp, status: "queued", error: null }); }));
    const user = userEvent.setup();
    renderApp("/experiments");
    expect(await screen.findByText("interrupted")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /#4 run a/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("resume to continue");
    expect(screen.getAllByText(/TEST DOUBLE/).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Resume experiment 4" }));
    expect(resumed).toBe(true);
  });
});
