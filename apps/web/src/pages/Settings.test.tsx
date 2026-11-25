import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { SystemInfo } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API response for UI tests only.
const info: SystemInfo = {
  version: "0.1.0", python: "3.11.9", platform: "Darwin", device: "mps", device_reason: "Apple GPU available",
  database: { ok: true, journal_mode: "wal", migration: "0008_m7_guard", head: "0008_m7_guard", backend: "sqlite" },
  models: [
    { key: "vlm-smolvlm-256m", model_id: "HuggingFaceTB/SmolVLM-256M-Instruct", task: "vision_language", revision: null, availability: "not_downloaded", test_double: false },
    { key: "tesseract-ocr", model_id: "tesseract", task: "ocr", revision: "5.3.4", availability: "available", test_double: false },
  ],
  ocr_languages: ["eng", "guj", "hin"],
  renderer: { engine: "chromium", playwright_installed: true, custom_executable: false, javascript: false, network: false },
  artifacts: { files: 3, bytes: 4096 },
  dependencies: [{ name: "torch", purpose: "neural model adapters", installed: false, version: null }, { name: "sklearn", purpose: "detector", installed: true, version: "1.5.2" }],
  test_doubles_enabled: false,
  limits: { max_upload_bytes: 10485760, max_input_codepoints: 20000 },
};

describe("Settings", () => {
  it("shows runtime, storage, revisions and dependencies", async () => {
    server.use(http.get("*/api/v1/system/info", () => HttpResponse.json(info)));
    renderApp("/settings");
    expect(await screen.findByText("eng, guj, hin")).toBeInTheDocument();
    expect(screen.getByTestId("ocr-project")).toHaveTextContent("guj Gujarati installed");
    expect(screen.getByText("not pinned")).toBeInTheDocument();
    expect(screen.getByText("not downloaded")).toBeInTheDocument();
    expect(screen.getByText("4.0 KB", { exact: false })).toBeInTheDocument();
    expect(screen.getByTestId("dep-torch")).toHaveTextContent("not installed");
    expect(screen.getByText("10.0 MB")).toBeInTheDocument();
    expect(screen.queryByTestId("test-doubles-enabled")).not.toBeInTheDocument();
  });

  it("flags a missing project OCR pack", async () => {
    server.use(http.get("*/api/v1/system/info", () => HttpResponse.json({ ...info, ocr_languages: ["eng", "hin"] })));
    renderApp("/settings");
    expect(await screen.findByText("guj Gujarati missing")).toBeInTheDocument();
  });

  it("toggles the theme", async () => {
    server.use(http.get("*/api/v1/system/info", () => HttpResponse.json(info)));
    const user = userEvent.setup();
    renderApp("/settings");
    await user.click(screen.getByRole("button", { name: "Use light theme" }));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    await user.click(screen.getByRole("button", { name: "Use dark theme" }));
  });

  it("shows an error state with retry", async () => {
    server.use(http.get("*/api/v1/system/info", () => HttpResponse.json({ error: { code: "x", message: "x" } }, { status: 500 })));
    renderApp("/settings");
    expect(await screen.findByText("System information unavailable.", {}, { timeout: 4000 })).toBeInTheDocument();
  });
});
