import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { MultimodalResult } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API response for UI tests only.
const result: MultimodalResult = {
  artifact_id: 1, image_url: "/api/v1/multimodal/artifacts/1/image", image_sha256: "c".repeat(64), width: 900, height: 96, renderer: "chromium",
  provenance: { browser: "153.0", javascript: false, network_requests_blocked: [] },
  ocr: { model: "tesseract-ocr", available: true, detail: "ok", text: "Log in at paypal today", confidence: 88, latency_ms: 120, error: null,
    comparison: { reference: "Log in at paypal today", reading: "Log in at paypal today", grapheme_error_rate: 0.04, exact_match: false, nfkc_casefold_match: false, hidden_codepoints_in_original: 0, hidden_codepoints_recovered: 0 },
    metadata: { missing_langs: ["guj"] } },
  vlm: { model: "vlm-smolvlm-256m", available: false, detail: "missing Python packages: torch, transformers", text: null, confidence: null, latency_ms: null, error: null, comparison: null, metadata: null },
};

describe("Multimodal Lab", () => {
  it("shows the render, OCR comparison, and an honest unavailable VLM", async () => {
    server.use(http.post("*/api/v1/multimodal/analyze", () => HttpResponse.json(result)));
    const user = userEvent.setup();
    renderApp("/multimodal");
    await user.click(screen.getByRole("button", { name: /render and read/i }));
    expect(await screen.findByTestId("mm-image")).toHaveAttribute("src", expect.stringContaining("/artifacts/1/image"));
    expect(screen.getByTestId("ocr-ger")).toHaveTextContent("0.040");
    expect(screen.getByTestId("vlm-unavailable")).toHaveTextContent("No reading is simulated");
    expect(screen.getByText(/Missing OCR language packs: guj/)).toBeInTheDocument();
  });
});
