import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { UnicodeAnalysis } from "../api/types";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Shape-correct API response for "a" + ZWSP + 😀 (values mirror the real engine).
const response: UnicodeAnalysis = {
  original: "a​\u{1F600}",
  sha256: "deadbeef".repeat(8),
  lengths: { codepoints: 3, graphemes: 3, utf8_bytes: 8, utf16_units: 4 },
  normalization: { is_nfc: true, is_nfd: true, is_nfkc: true, is_nfkd: true },
  graphemes: [
    { index: 0, text: "a", span: span(0, 1, 0, 1, 0, 1), codepoint_count: 1 },
    { index: 1, text: "​", span: span(1, 2, 1, 4, 1, 2), codepoint_count: 1 },
    { index: 2, text: "\u{1F600}", span: span(2, 3, 4, 8, 2, 4), codepoint_count: 1 },
  ],
  codepoints: [
    cp(0, "a", "U+0061", "LATIN SMALL LETTER A", "Ll", "61", span(0, 1, 0, 1, 0, 1), [], false),
    cp(1, "​", "U+200B", "ZERO WIDTH SPACE", "Cf", "E2 80 8B", span(1, 2, 1, 4, 1, 2), ["zero_width"], true),
    cp(2, "\u{1F600}", "U+1F600", "GRINNING FACE", "So", "F0 9F 98 80", span(2, 3, 4, 8, 2, 4), [], false),
  ],
  invisible_count: 1,
  engine: { engine_version: "0.1.0", unicodedata_version: "14.0.0", regex_version: "2.5" },
};

function span(a: number, b: number, c: number, d: number, e: number, f: number) {
  return { cp_start: a, cp_end: b, utf8_start: c, utf8_end: d, utf16_start: e, utf16_end: f };
}
function cp(
  index: number,
  char: string,
  codepoint: string,
  name: string,
  category: string,
  utf8_hex: string,
  s: ReturnType<typeof span>,
  kinds: UnicodeAnalysis["codepoints"][number]["kinds"],
  invisible: boolean,
) {
  return {
    index, char, codepoint, name, category, bidi_class: "L", combining_class: 0,
    utf8_hex, span: s, kinds, invisible,
  };
}

describe("Unicode Inspector", () => {
  it("sends the exact input, including invisible characters", async () => {
    let received: unknown;
    server.use(
      http.post("*/api/v1/unicode/analyze", async ({ request }) => {
        received = await request.json();
        return HttpResponse.json(response);
      }),
    );
    const user = userEvent.setup();
    renderApp("/inspector");
    const box = screen.getByLabelText("Original text");
    // fireEvent keeps the exact string; userEvent.type would interpret special chars.
    fireEvent.change(box, { target: { value: "  a​\u{1F600}\n" } });
    await user.click(screen.getByRole("button", { name: /analyse/i }));
    await screen.findByTestId("sha256");
    expect(received).toEqual({ text: "  a​\u{1F600}\n" });
  });

  it("renders integrity, graphemes, code points and invisible markers", async () => {
    server.use(http.post("*/api/v1/unicode/analyze", () => HttpResponse.json(response)));
    const user = userEvent.setup();
    renderApp("/inspector");
    await user.click(screen.getByRole("button", { name: /analyse/i }));
    expect(await screen.findByTestId("sha256")).toHaveTextContent(response.sha256);
    expect(screen.getByText("ZERO WIDTH SPACE")).toBeInTheDocument();
    expect(screen.getByText("zero_width")).toBeInTheDocument();
    expect(screen.getByText("invisible: 1")).toBeInTheDocument();
    expect(screen.getByText("F0 9F 98 80")).toBeInTheDocument();
    expect(screen.getByText("2–4")).toBeInTheDocument(); // UTF-16 span of the emoji
  });

  it("highlights the code points of a selected grapheme", async () => {
    server.use(http.post("*/api/v1/unicode/analyze", () => HttpResponse.json(response)));
    const user = userEvent.setup();
    renderApp("/inspector");
    await user.click(screen.getByRole("button", { name: /analyse/i }));
    const items = await screen.findAllByRole("button", { name: /^Grapheme \d+$/ });
    await user.click(items[2]!);
    expect(items[2]).toHaveAttribute("aria-pressed", "true");
    const rows = document.querySelectorAll('tr[data-selected="true"]');
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("U+1F600");
  });

  it("shows structured API errors such as invalid_unicode", async () => {
    server.use(
      http.post("*/api/v1/unicode/analyze", () =>
        HttpResponse.json(
          { error: { code: "invalid_unicode", message: "Input is not well-formed Unicode." } },
          { status: 422 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp("/inspector");
    await user.click(screen.getByRole("button", { name: /analyse/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("invalid_unicode");
  });
});
