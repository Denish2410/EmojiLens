import { useMutation } from "@tanstack/react-query";
import clsx from "clsx";
import { Copy, ScanSearch } from "lucide-react";
import { useState } from "react";
import { ApiError, api } from "../api/client";
import type { Codepoint, UnicodeAnalysis } from "../api/types";
import { EvidencePanel, type Selection } from "../components/inspector/EvidencePanel";
import { ViewsPanel } from "../components/inspector/ViewsPanel";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, CardHeader } from "../components/ui";
import { copyText } from "../lib/clipboard";

const SAMPLE =
  "Hi\u200b 👨\u200d👩\u200d👧 👍\u{1F3FD} 1\ufe0f\u20e3 🇮🇳 क्\u200dष ક્\u200cષ";

const KIND_TONE: Record<string, "cyan" | "violet" | "amber" | "neutral"> = {
  zero_width: "amber",
  bidi_control: "amber",
  tag: "amber",
  filler: "amber",
  control: "amber",
  joiner: "cyan",
  variation_selector: "cyan",
  format: "neutral",
  emoji_modifier: "violet",
  regional_indicator: "violet",
  combining_enclosing_keycap: "violet",
};

/** A visible stand-in for code points that render as nothing. */
function glyph(c: Codepoint): string {
  if (c.invisible) return "·";
  if (c.char === " ") return "␠";
  if (c.char === "\n") return "↵";
  if (c.char === "\t") return "⇥";
  return c.char;
}

/** Show a grapheme as rendered; stand in only when nothing would be visible. */
function graphemeDisplay(text: string, cps: Codepoint[]): string {
  if (cps.length > 0 && cps.every((c) => c.invisible)) return "·";
  if (cps.length === 1 && cps[0]) return glyph(cps[0]);
  return text;
}

export function UnicodeInspector() {
  const [text, setText] = useState(SAMPLE);
  const [selection, setSelection] = useState<Selection | null>(null);
  const toast = useToast();
  const mutation = useMutation<UnicodeAnalysis, ApiError, string>({
    mutationFn: api.analyzeUnicode,
    onSuccess: () => setSelection(null),
  });
  const result = mutation.data;

  const copy = async (value: string, label: string) => {
    const ok = await copyText(value);
    toast(ok ? `${label} copied` : "Clipboard unavailable", ok ? "ok" : "error");
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Unicode Inspector</h1>
        <p className="mt-1 text-sm text-muted">
          Inspect code points, grapheme clusters and byte offsets. Input is analysed exactly as
          entered and is never trimmed or normalized.
        </p>
      </div>

      <Card>
        <CardHeader
          title={<label htmlFor="inspector-input">Original text</label>}
          actions={
            <div className="flex gap-2">
              <Button onClick={() => void copy(text, "Original")} aria-label="Copy original text">
                <Copy className="size-3.5" /> Copy original
              </Button>
              <Button
                variant="primary"
                onClick={() => mutation.mutate(text)}
                disabled={mutation.isPending}
              >
                <ScanSearch className="size-3.5" />
                {mutation.isPending ? "Analysing…" : "Analyse"}
              </Button>
            </div>
          }
        />
        <textarea
          id="inspector-input"
          value={text}
          spellCheck={false}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) mutation.mutate(text);
          }}
          rows={4}
          className="block w-full resize-y rounded-b-xl bg-transparent p-4 text-base outline-none"
          aria-describedby="inspector-hint"
        />
        <p id="inspector-hint" className="border-t border-line px-4 py-2 text-xs text-muted">
          Press Ctrl/⌘ + Enter to analyse.
        </p>
      </Card>

      {mutation.isError && (
        <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm">
          <span className="font-mono text-red-500">{mutation.error.code}</span>{" "}
          {mutation.error.message}
        </div>
      )}

      {!result && !mutation.isError && (
        <Card className="p-8 text-center text-sm text-muted">
          Enter text and run an analysis to see its graphemes and code points.
        </Card>
      )}

      {result && (
        <>
          <Card>
            <CardHeader title="Integrity" />
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 p-4 text-sm sm:grid-cols-4">
              {(
                [
                  ["Code points", result.lengths.codepoints],
                  ["Graphemes", result.lengths.graphemes],
                  ["UTF-8 bytes", result.lengths.utf8_bytes],
                  ["UTF-16 units", result.lengths.utf16_units],
                ] as const
              ).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-xs text-muted">{k}</dt>
                  <dd className="font-mono text-lg">{v}</dd>
                </div>
              ))}
              <div className="col-span-2 sm:col-span-4">
                <dt className="text-xs text-muted">SHA-256 (original UTF-8)</dt>
                <dd className="flex items-center gap-2">
                  <code className="font-mono text-xs break-all" data-testid="sha256">
                    {result.sha256}
                  </code>
                  <button
                    type="button"
                    aria-label="Copy SHA-256"
                    onClick={() => void copy(result.sha256, "SHA-256")}
                    className="rounded p-1 text-muted hover:bg-surface-2"
                  >
                    <Copy className="size-3.5" />
                  </button>
                </dd>
              </div>
              <div className="col-span-2 flex flex-wrap gap-1.5 sm:col-span-4">
                {(["is_nfc", "is_nfd", "is_nfkc", "is_nfkd"] as const).map((k) => (
                  <Badge key={k} tone={result.normalization[k] ? "emerald" : "neutral"}>
                    {k.slice(3).toUpperCase()}: {result.normalization[k] ? "yes" : "no"}
                  </Badge>
                ))}
                <Badge tone={result.invisible_count ? "amber" : "neutral"}>
                  invisible: {result.invisible_count}
                </Badge>
                {Object.entries(result.scripts.counts).map(([script, n]) => (
                  <Badge key={script} tone="cyan">
                    {script}: {n}
                  </Badge>
                ))}
                {result.scripts.is_mixed && <Badge tone="neutral">mixed scripts</Badge>}
              </div>
            </dl>
          </Card>

          <EvidencePanel
            evidence={result.evidence}
            selection={selection}
            onSelect={setSelection}
          />

          <ViewsPanel
            original={result.original}
            views={result.views}
            selection={selection}
            onSelect={setSelection}
          />

          <Card>
            <CardHeader title="Grapheme clusters" />
            <ul className="flex flex-wrap gap-1.5 p-4" aria-label="Grapheme clusters">
              {result.graphemes.map((g) => {
                const cps = result.codepoints.slice(g.span.cp_start, g.span.cp_end);
                const hasInvisible = cps.some((c) => c.invisible);
                const gid = `grapheme:${g.index}`;
                const inSel =
                  selection !== null &&
                  g.span.cp_start < selection.end &&
                  g.span.cp_end > selection.start;
                return (
                  <li key={g.index}>
                  <button
                    type="button"
                    aria-label={`Grapheme ${g.index}`}
                    onClick={() =>
                      setSelection(
                        selection?.source === gid
                          ? null
                          : { start: g.span.cp_start, end: g.span.cp_end, source: gid },
                      )
                    }
                    aria-pressed={selection?.source === gid}
                    title={`#${g.index} · ${g.codepoint_count} code point(s) · UTF-16 ${g.span.utf16_start}–${g.span.utf16_end}`}
                    className={clsx(
                      "flex min-w-9 flex-col items-center rounded-md border px-1.5 py-1 transition-colors",
                      inSel
                        ? "border-violet-500 bg-violet-500/10"
                        : hasInvisible
                          ? "border-amber-500/40 bg-amber-500/5"
                          : "border-line hover:bg-surface-2",
                    )}
                  >
                    <span className="text-lg leading-6">{graphemeDisplay(g.text, cps)}</span>
                    <span className="font-mono text-[10px] text-muted">{g.codepoint_count}</span>
                  </button>
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card>
            <CardHeader
              title="Code points"
              actions={
                selection && (
                  <Button onClick={() => setSelection(null)}>
                    Clear selection (cp {selection.start}–{selection.end})
                  </Button>
                )
              }
            />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-muted">
                  <tr className="border-b border-line">
                    {["#", "Char", "Code point", "Name", "Cat", "UTF-8", "UTF-16", "Markers"].map(
                      (h) => (
                        <th key={h} scope="col" className="px-3 py-2 font-medium whitespace-nowrap">
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody className="font-mono text-xs">
                  {result.codepoints.map((c) => {
                    const inSel =
                      selection !== null && c.index >= selection.start && c.index < selection.end;
                    return (
                      <tr
                        key={c.index}
                        data-selected={inSel ? "true" : undefined}
                        className={clsx(
                          "border-b border-line/60",
                          inSel && "bg-violet-500/10",
                          c.invisible && !inSel && "bg-amber-500/5",
                        )}
                      >
                        <td className="px-3 py-1.5 text-muted">{c.index}</td>
                        <td className="px-3 py-1.5 font-sans text-base">{glyph(c)}</td>
                        <td className="px-3 py-1.5 whitespace-nowrap">{c.codepoint}</td>
                        <td className="px-3 py-1.5 whitespace-nowrap">{c.name}</td>
                        <td className="px-3 py-1.5">{c.category}</td>
                        <td className="px-3 py-1.5 whitespace-nowrap">{c.utf8_hex}</td>
                        <td className="px-3 py-1.5 whitespace-nowrap">
                          {c.span.utf16_start}–{c.span.utf16_end}
                        </td>
                        <td className="px-3 py-1.5">
                          <div className="flex flex-wrap gap-1">
                            {c.kinds.map((k) => (
                              <Badge key={k} tone={KIND_TONE[k] ?? "neutral"}>
                                {k}
                              </Badge>
                            ))}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="border-t border-line px-4 py-2 text-xs text-muted">
              Markers describe structure only. They are not risk verdicts: joiners and variation
              selectors are legitimate in emoji sequences and in Devanagari or Gujarati text.
              Engine {result.engine.engine_version} · rules {result.engine.ruleset_version} ·
              Unicode data {result.engine.unicodedata_version} · regex{" "}
              {result.engine.regex_version} · emoji {result.engine.emoji_version}
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
