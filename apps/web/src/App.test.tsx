import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "./test/server";
import { renderApp } from "./test/render";

describe("Overview", () => {
  it("shows live API status from the backend", async () => {
    renderApp("/");
    expect(await screen.findByText(/API 0\.1\.0 is live/)).toBeInTheDocument();
    expect(screen.getByText("journal_mode=wal")).toBeInTheDocument();
  });

  it("shows an empty research state instead of invented metrics", async () => {
    renderApp("/");
    expect(await screen.findByTestId("dashboard-empty")).toHaveTextContent("No datasets have been imported yet");
    expect(screen.getByText(/nothing reportable/)).toBeInTheDocument();
    expect(screen.getByTestId("readiness-evaluation_dataset")).toHaveTextContent("Frozen evaluation dataset");
  });

  it("shows stored counts from the dashboard summary", async () => {
    // Mocked API response for a UI test only.
    server.use(
      http.get("*/api/v1/dashboard/summary", () =>
        HttpResponse.json({
          datasets: { total: 2, by_kind: { evaluation: 1, synthetic_fixture: 1 }, versions: 3, frozen_versions: 2, sources: 1234 },
          languages: { en: 700, "hi-Latn": 534 },
          transforms: { variants: 40, invalid_variants: 1, recipes: 2, families: ["homoglyph", "emoji_cipher"] },
          annotation: { annotators: 2, annotations: 10, adjudications: 3 },
          models: { catalogue: 5, test_doubles: 0, availability: { available: 2 } },
          experiments: { by_status: { completed: 1, interrupted: 1 }, outputs: 80, failed_outputs: 4, test_double_outputs: 0, reportable: 1 },
          crsc: { metric_rows: 12, experiments: 1 },
          multimodal: { render_artifacts: 5 },
          guard: { evaluations: 1, detector_artifacts: 1 },
          readiness: [],
          reportable: true,
        }),
      ),
    );
    renderApp("/");
    expect(await screen.findByText("1,234")).toBeInTheDocument();
    expect(screen.getByText("reportable results stored")).toBeInTheDocument();
    expect(screen.getByTitle("hi-Latn: 534 source records")).toBeInTheDocument();
    expect(screen.getByTitle("gu: 0 source records")).toBeInTheDocument();
    expect(screen.getByText("emoji_cipher")).toBeInTheDocument();
    expect(screen.queryByTestId("dashboard-empty")).not.toBeInTheDocument();
  });

  it("shows an error with retry when the summary cannot load", async () => {
    server.use(http.get("*/api/v1/dashboard/summary", () => HttpResponse.json({ error: { code: "boom", message: "x" } }, { status: 500 })));
    renderApp("/");
    expect(await screen.findByText("Research summary unavailable.", {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("shows an error state with retry when the API is down", async () => {
    server.use(http.get("*/api/v1/health", () => HttpResponse.error()));
    renderApp("/");
    expect(await screen.findByText("API unreachable", {}, { timeout: 4000 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refresh system status/i })).toBeEnabled();
  });
});

describe("Shell", () => {
  it("toggles theme and persists it", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("button", { name: /switch to light theme/i }));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(localStorage.getItem("emojilens-theme")).toBe("light");
    await user.click(screen.getByRole("button", { name: /switch to dark theme/i }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("opens and closes the mobile navigation drawer", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("button", { name: /open navigation/i }));
    const dialog = screen.getByRole("dialog", { name: "Navigation" });
    await user.click(within(dialog).getByRole("link", { name: /unicode inspector/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Unicode Inspector" })).toBeInTheDocument();
  });

  it("closes the drawer with Escape", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("button", { name: /open navigation/i }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders a not-found page", () => {
    renderApp("/does-not-exist");
    expect(screen.getByRole("heading", { name: /page not found/i })).toBeInTheDocument();
  });
});
