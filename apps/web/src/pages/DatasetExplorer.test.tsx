import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { Dataset, SourcePage, VersionDetail } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API responses for UI tests only.
const version = {
  number: 1,
  content_sha256: "ab".repeat(32),
  record_count: 2,
  schema_version: 1,
  split_seed: null,
  split_ratios: null,
  split_method: null,
  frozen_at: null,
  created_at: "2026-11-24T00:00:00Z",
};
const dataset: Dataset = {
  slug: "demo",
  name: "Demo set",
  description: "",
  kind: "synthetic_fixture",
  license: "CC0-1.0",
  created_at: "2026-11-24T00:00:00Z",
  versions: [version],
};
const detail = (frozen: boolean): VersionDetail => ({
  dataset: "demo",
  version: frozen ? { ...version, frozen_at: "2026-11-24T01:00:00Z", split_seed: 7, split_ratios: [0.7, 0.15, 0.15], split_method: "sha256-group-bucket/1" } : version,
  stats: { language: { en: 1, hi: 1 }, split: frozen ? { train: 2 } : { "(none)": 2 }, safety_label: { safe: 2 }, control: { clean: 2 } },
  language_agreement: { agree: 2, disagree: 0, undetected: 0 },
  leakage: [],
  leakage_checked: frozen,
});
const page: SourcePage = {
  total: 2,
  page: 1,
  page_size: 25,
  items: [
    { external_id: "a", source_group: "a", text: "hello", text_sha256: "x", language: "en", detected_language: "en", detected_confidence: 1, safety_label: "safe", control: "clean", origin: "o", license: "l", meta: {}, split: null },
    { external_id: "b", source_group: "b", text: "नमस्ते", text_sha256: "y", language: "hi", detected_language: "hi", detected_confidence: 1, safety_label: "safe", control: "clean", origin: "o", license: "l", meta: {}, split: null },
  ],
};

describe("Dataset Explorer", () => {
  it("shows an empty state when there are no datasets", async () => {
    server.use(http.get("*/api/v1/datasets", () => HttpResponse.json([])));
    renderApp("/datasets");
    expect(await screen.findByText(/No datasets yet/)).toBeInTheDocument();
  });

  it("creates a dataset with validated fields", async () => {
    let body: unknown;
    server.use(
      http.get("*/api/v1/datasets", () => HttpResponse.json([])),
      http.post("*/api/v1/datasets", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...dataset, versions: [] }, { status: 201 });
      }),
      http.get("*/api/v1/datasets/demo", () => HttpResponse.json({ ...dataset, versions: [] })),
    );
    const user = userEvent.setup();
    renderApp("/datasets");
    await user.click(screen.getByRole("button", { name: /new dataset/i }));
    const form = screen.getByRole("form", { name: "New dataset" });
    await user.type(within(form).getByLabelText("Slug"), "demo");
    await user.type(within(form).getByLabelText("Name"), "Demo set");
    await user.type(within(form).getByLabelText("License"), "CC0-1.0");
    await user.click(within(form).getByRole("button", { name: /create dataset/i }));
    expect(await screen.findByText(/No versions yet/)).toBeInTheDocument();
    expect(body).toMatchObject({ slug: "demo", kind: "evaluation", license: "CC0-1.0" });
  });

  it("shows version integrity, synthetic warning, sources and freezes splits", async () => {
    let frozen = false;
    server.use(
      http.get("*/api/v1/datasets", () => HttpResponse.json([dataset])),
      http.get("*/api/v1/datasets/demo", () => HttpResponse.json(dataset)),
      http.get("*/api/v1/datasets/demo/versions/1", () => HttpResponse.json(detail(frozen))),
      http.get("*/api/v1/datasets/demo/versions/1/sources", () => HttpResponse.json(page)),
      http.post("*/api/v1/datasets/demo/versions/1/freeze", () => {
        frozen = true;
        return HttpResponse.json(detail(true));
      }),
    );
    const user = userEvent.setup();
    renderApp("/datasets/demo");
    expect(await screen.findByTestId("content-hash")).toHaveTextContent("ab".repeat(32));
    expect(screen.getByText(/excluded from every reported research result/)).toBeInTheDocument();
    expect(await screen.findByText("नमस्ते")).toBeInTheDocument();
    expect(screen.getByText(/validated when the version is frozen/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /freeze splits/i }));
    expect(await screen.findByTestId("leakage-ok")).toBeInTheDocument();
  });

  it("shows line-numbered import errors", async () => {
    server.use(
      http.get("*/api/v1/datasets", () => HttpResponse.json([dataset])),
      http.get("*/api/v1/datasets/demo", () => HttpResponse.json(dataset)),
      http.get("*/api/v1/datasets/demo/versions/1", () => HttpResponse.json(detail(false))),
      http.get("*/api/v1/datasets/demo/versions/1/sources", () => HttpResponse.json(page)),
      http.post("*/api/v1/datasets/demo/versions", () =>
        HttpResponse.json(
          {
            error: {
              code: "dataset_validation_failed",
              message: "1 line(s) failed validation; nothing was imported.",
              details: { errors: [{ line: 2, code: "invalid_json", message: "Invalid JSON at column 2." }] },
            },
          },
          { status: 422 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp("/datasets/demo");
    const input = await screen.findByLabelText(/import jsonl/i);
    await user.upload(input, new File(['{"id":"a"}\n{bad'], "x.jsonl", { type: "application/x-ndjson" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("line 2 · invalid_json");
  });
});
