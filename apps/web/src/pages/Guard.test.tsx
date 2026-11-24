import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { GuardAssessment, GuardEvaluationResult, MetricsRow } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API responses for UI tests only.
const assessment: GuardAssessment = {
  input_sha256: "a".repeat(64), guard_version: "0.1.0", ablation: "full",
  evidence: [{ id: "zero_width.inside_word@4-5", rule: "zero_width.inside_word", category: "suspicious", cp_start: 4, cp_end: 5, utf16_start: 4, utf16_end: 5, message: "splits a word" }],
  indicators: {}, rule_score: 0.5, detector_score: null, detector_version: null, risk_score: 0.5, uncertainty: "unquantified (single component)",
  contributions: [{ source: "rule", name: "zero_width.inside_word", weight: 0.5, evidence_ids: ["zero_width.inside_word@4-5"], detail: "splits a word" }],
  explanation: [], recommendation: "request_review", relevant_views: ["sanitized"], latency_ms: 3, notes: ["no trained detector loaded; rules only"],
};
const m = (tp: number, fp: number, tn: number, fn: number): MetricsRow => ({ n: tp + fp + tn + fn, tp, fp, tn, fn, precision: 0.5, recall: 0.5, f1: 0.5, fpr: 0.1, fnr: 0.5, f1_ci: [0.3, 0.7], mean_latency_ms: 1, false_positives: fp ? ["benign-001"] : [], false_negatives: [] });
const evaluation: GuardEvaluationResult = {
  id: 1, config: { split: "test", decision_threshold: 0.3, dataset: "d", version: 1 }, research_reportable: false,
  results: {
    systems: { no_defence: { kind: "baseline", overall: m(0, 0, 5, 5), strata: {} }, emojiguard_full: { kind: "emojiguard", overall: m(4, 1, 4, 1), strata: { language: { en: m(2, 1, 2, 0) } } } },
    unavailable: { offtheshelf_classifier: "no installed safety classifier" },
    items: { "benign-001": { text: "Happy birthday", label: 0, language: "en", family: "source" } },
  },
};

describe("EmojiGuard Console", () => {
  it("shows recommendation, scores, located contributions and notes", async () => {
    server.use(http.get("*/api/v1/guard/detectors", () => HttpResponse.json([])), http.post("*/api/v1/guard/assess", () => HttpResponse.json(assessment)));
    const user = userEvent.setup();
    renderApp("/guard");
    await user.click(screen.getByRole("button", { name: /^assess$/i }));
    expect(await screen.findByTestId("guard-recommendation")).toHaveTextContent("Request review");
    expect(screen.getByTestId("guard-detector")).toHaveTextContent("—");
    expect(screen.getByRole("list", { name: "Contributions" })).toHaveTextContent("zero_width.inside_word@4-5");
    expect(screen.getByText(/no trained detector/)).toBeInTheDocument();
  });
});

describe("Evaluation Dashboard", () => {
  it("compares systems, flags synthetic evaluations and lists false positives", async () => {
    server.use(
      http.get("*/api/v1/guard/evaluations", () => HttpResponse.json([{ id: 1, config: evaluation.config, created_at: "2026-11-25T00:00:00Z" }])),
      http.get("*/api/v1/guard/evaluations/1", () => HttpResponse.json(evaluation)),
      http.get("*/api/v1/guard/detectors", () => HttpResponse.json([])),
      http.get("*/api/v1/datasets", () => HttpResponse.json([])),
    );
    renderApp("/evaluation");
    expect(await screen.findByTestId("eval-not-reportable")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "System comparison" })).toHaveTextContent("emojiguard_full");
    expect(screen.getByText(/offtheshelf_classifier/).closest("li")).toHaveTextContent("unavailable");
    expect(screen.getByRole("list", { name: "false_positives" })).toHaveTextContent("Happy birthday");
  });
});
