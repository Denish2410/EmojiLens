import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { ApplyResult, TransformSpec } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API responses for UI tests only.
const specs: TransformSpec[] = [
  {
    id: "homoglyph",
    version: "1.0.0",
    family: "homoglyph",
    description: "Swaps look-alikes.",
    varieties: ["en"],
    params: [{ name: "rate", kind: "float", default: 0.5, description: "rate", choices: [], minimum: 0, maximum: 1 }],
    seeded: true,
    reversible: false,
  },
  {
    id: "unicode_smuggling",
    version: "1.0.0",
    family: "unicode_smuggling",
    description: "Hides content.",
    varieties: ["en"],
    params: [
      { name: "method", kind: "choice", default: "zero_width_split", description: "m", choices: ["zero_width_split", "tag_payload"], minimum: null, maximum: null },
    ],
    seeded: true,
    reversible: true,
  },
];
const result: ApplyResult = {
  original: "pay",
  original_sha256: "a".repeat(64),
  output: "p\u0430y\u200b",
  output_sha256: "b".repeat(64),
  variety: "en",
  seed: 7,
  chain_hash: "c".repeat(64),
  valid: true,
  steps: [
    {
      transform_id: "homoglyph",
      version: "1.0.0",
      family: "homoglyph",
      params: { rate: 0.5 },
      seed: 7000,
      output: "p\u0430y",
      edits: 1,
      valid: true,
      checks: { output_well_formed: true, pieces_tile_original: true, changed: true, round_trip: null },
      notes: [],
      provenance: {},
      pieces: [[0, 1, "p"], [1, 2, "\u0430"], [2, 3, "y"]],
    },
  ],
  pieces: [[0, 1, "p"], [1, 2, "\u0430"], [2, 3, "y\u200b"]],
};

describe("Transformation Lab", () => {
  it("builds a chain from specs, sends exact params and shows results", async () => {
    let sent: unknown;
    server.use(
      http.get("*/api/v1/transforms", () => HttpResponse.json(specs)),
      http.get("*/api/v1/datasets", () => HttpResponse.json([])),
      http.post("*/api/v1/transforms/apply", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(result);
      }),
    );
    const user = userEvent.setup();
    renderApp("/transforms");
    expect(screen.getByRole("button", { name: /run chain/i })).toBeDisabled();
    await screen.findByRole("option", { name: /homoglyph · homoglyph/ });
    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await user.selectOptions(screen.getByLabelText("Transformation to add"), "unicode_smuggling");
    await user.click(screen.getByRole("button", { name: /^add$/i }));
    const steps = screen.getByRole("list", { name: "Chain steps" });
    expect(within(steps).getAllByRole("listitem")).toHaveLength(2);
    await user.selectOptions(within(steps).getByLabelText("method"), "tag_payload");
    await user.click(screen.getByRole("button", { name: /run chain/i }));
    expect(await screen.findByTestId("chain-hash")).toHaveTextContent("c".repeat(64));
    expect(sent).toMatchObject({
      seed: 7,
      variety: "en",
      chain: [
        { transform_id: "homoglyph", params: { rate: 0.5 } },
        { transform_id: "unicode_smuggling", params: { method: "tag_payload" } },
      ],
    });
    expect(screen.getByLabelText("Transformed with invisible characters revealed")).toHaveTextContent("<U+200B>");
    expect(screen.getByText(/round_trip: n\/a/)).toBeInTheDocument();
  });

  it("removes and reorders steps", async () => {
    server.use(
      http.get("*/api/v1/transforms", () => HttpResponse.json(specs)),
      http.get("*/api/v1/datasets", () => HttpResponse.json([])),
    );
    const user = userEvent.setup();
    renderApp("/transforms");
    await screen.findByRole("option", { name: /homoglyph · homoglyph/ });
    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await user.selectOptions(screen.getByLabelText("Transformation to add"), "unicode_smuggling");
    await user.click(screen.getByRole("button", { name: /^add$/i }));
    await user.click(screen.getByRole("button", { name: "Move step 2 up" }));
    const items = within(screen.getByRole("list", { name: "Chain steps" })).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("unicode_smuggling");
    await user.click(screen.getByRole("button", { name: "Remove step 1" }));
    expect(within(screen.getByRole("list", { name: "Chain steps" })).getAllByRole("listitem")).toHaveLength(1);
  });
});
