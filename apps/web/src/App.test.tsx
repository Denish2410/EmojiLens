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
    expect(screen.getByText(/No datasets or experiments exist yet/)).toBeInTheDocument();
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
