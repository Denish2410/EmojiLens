import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { MultilingualResult } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API response for UI tests only.
const result: MultilingualResult = {
  identification: {
    label: "gu-Latn",
    confidence: 0.83,
    uncertain: true,
    reasons: ["thin evidence: 2 identified token(s)"],
    scores: { "gu-Latn": 2.5, "hi-Latn": 0.5 },
    code_mixed: false,
    cmi: 0,
    switch_points: 0,
    method: "script+lexicon/0.1.0",
  },
  tokens: [
    { text: "kem", cp_start: 0, cp_end: 3, tag: "gu-Latn", candidates: ["gu-Latn"] },
    { text: "\u{1F44D}", cp_start: 4, cp_end: 5, tag: "emoji", candidates: [] },
  ],
  scripts: { Latin: 3 },
  dominant_script: "Latin",
  emoji: [
    {
      emoji: "\u{1F44D}",
      cp_start: 4,
      cp_end: 5,
      meanings: [
        { variety: "en", locale: "en", name: "thumbs up", keywords: [], fallback: false },
        { variety: "gu-Latn", locale: "gu", name: "gu-name", keywords: [], fallback: true },
      ],
    },
  ],
  cldr_version: "49.0.0",
};

describe("Multilingual Lab", () => {
  it("shows identification with uncertainty, tokens and CLDR meanings with fallbacks", async () => {
    server.use(
      http.get("*/api/v1/multilingual/varieties", () =>
        HttpResponse.json([{ code: "gu-Latn", name: "Romanized Gujarati", script: "Latin", cldr_locale: null, notes: "" }]),
      ),
      http.post("*/api/v1/multilingual/analyze", () => HttpResponse.json(result)),
    );
    const user = userEvent.setup();
    renderApp("/multilingual");
    await user.click(screen.getByRole("button", { name: /^analyse$/i }));
    expect(await screen.findByTestId("variety-label")).toHaveTextContent("Romanized Gujarati");
    expect(screen.getByText("uncertain")).toBeInTheDocument();
    expect(screen.getByText(/thin evidence/)).toBeInTheDocument();
    expect(screen.getByText("thumbs up")).toBeInTheDocument();
    expect(screen.getByText("fallback: gu")).toBeInTheDocument();
    expect(screen.getByText(/CLDR 49\.0\.0/)).toBeInTheDocument();
  });
});
