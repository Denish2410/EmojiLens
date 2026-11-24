import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { InferResult, ModelsInfo } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API responses for UI tests only.
const info = (avail: boolean): ModelsInfo => ({
  device: "cpu",
  device_reason: "torch not installed",
  resources: { available_ram_gb: null, free_disk_gb: 30, cache_dir: "/x" },
  models: [
    { key: "embed-x", model_id: "org/embed-x", adapter: "st_embedding", capabilities: ["TOKENIZE", "EMBED"], license: "Apache-2.0", revision: null, languages: ["en"], approx_ram_gb: 1, approx_disk_gb: 0.5, notes: "", test_double: false, availability: "not_downloaded", availability_detail: "no exact revision pinned", loaded: false },
    { key: "td", model_id: "test-double/td", adapter: "test_double", capabilities: ["TOKENIZE"], license: "n/a", revision: "test-double", languages: [], approx_ram_gb: 0, approx_disk_gb: 0, notes: "", test_double: true, availability: avail ? "available" : "not_downloaded", availability_detail: "ready", loaded: false },
  ],
});
const tdResult: InferResult = {
  model: "td", capability: "TOKENIZE", raw_output: ["kal"], normalized: { length: 1 }, latency_ms: 0.4,
  tokenization: { tokens: ["kal", "milte"], ids: [1, 2], offsets: [[0, 3], [4, 9]], unknown: 0 },
  metadata: { model_id: "test-double/td", revision: "test-double", device: "cpu", adapter_version: "1.0.0", test_double: true, library_versions: {} },
  error: null,
};

describe("Model Arena", () => {
  it("shows registry availability honestly and an empty state when nothing is installed", async () => {
    server.use(http.get("*/api/v1/models", () => HttpResponse.json(info(false))));
    renderApp("/models");
    expect(await screen.findByText("not pinned")).toBeInTheDocument();
    expect(screen.getAllByText("not downloaded").length).toBeGreaterThan(0);
    expect(screen.getByTestId("no-models")).toHaveTextContent("Nothing is simulated");
    expect(screen.getByRole("checkbox", { name: "embed-x" })).toBeDisabled();
  });

  it("labels test-double results as not model results", async () => {
    server.use(
      http.get("*/api/v1/models", () => HttpResponse.json(info(true))),
      http.post("*/api/v1/models/td/infer", () => HttpResponse.json(tdResult)),
    );
    const user = userEvent.setup();
    renderApp("/models");
    await user.click(await screen.findByRole("checkbox", { name: "td" }));
    await user.click(screen.getByRole("button", { name: /^run$/i }));
    const card = await screen.findByTestId("arena-result");
    expect(card).toHaveTextContent("TEST DOUBLE");
    expect(screen.getByRole("list", { name: "td tokens" })).toHaveTextContent("milte");
  });
});
