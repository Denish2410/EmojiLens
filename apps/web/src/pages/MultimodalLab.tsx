import { useMutation } from "@tanstack/react-query";
import clsx from "clsx";
import { Eye, Image as ImageIcon, ScanText } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { ApiError, API_BASE, api } from "../api/client";
import type { MultimodalResult, Reading } from "../api/types";
import { Badge, Button, Card, CardHeader } from "../components/ui";
import { countInvisible, revealInvisible } from "../lib/visible";

const SAMPLES: Record<string, string> = {
  homoglyph: "Log in at p\u0430ypal today \u{1F44D}",
  hindi: "आज मौसम बहुत अच्छा है",
  hidden: "Nice day" + Array.from("note", (c) => String.fromCodePoint(0xe0000 + c.charCodeAt(0))).join(""),
  styled: "\u{1D407}\u{1D41E}\u{1D425}\u{1D425}\u{1D428} world",
};

function ReadingCard({ title, icon, r }: { title: string; icon: React.ReactNode; r: Reading }) {
  const c = r.comparison;
  return (
    <Card className="min-w-0">
      <CardHeader title={<span className="flex items-center gap-2">{icon}{title}</span>} actions={<Badge tone={r.available ? (r.error ? "red" : "emerald") : "amber"}>{r.available ? (r.error ? "error" : "read") : "unavailable"}</Badge>} />
      <div className="flex flex-col gap-3 p-4 text-sm">
        <p className="font-mono text-xs text-muted">{r.model}</p>
        {!r.available ? (
          <p data-testid={`${title.toLowerCase()}-unavailable`}>Not available: {r.detail}. No reading is simulated.</p>
        ) : r.error ? (
          <p role="alert" className="text-red-500">{r.error.code}: {r.error.message}</p>
        ) : (
          <>
            <p className="rounded-md bg-surface-2 p-3 text-base break-words whitespace-pre-wrap" data-testid={`${title.toLowerCase()}-text`}>{r.text || "(no text read)"}</p>
            {c && (
              <dl className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
                <div><dt className="text-muted">Grapheme error rate</dt><dd className="font-mono" data-testid={`${title.toLowerCase()}-ger`}>{c.grapheme_error_rate === null ? "—" : c.grapheme_error_rate.toFixed(3)}</dd></div>
                <div><dt className="text-muted">Exact match</dt><dd className="font-mono">{String(c.exact_match)}</dd></div>
                <div><dt className="text-muted">NFKC + casefold match</dt><dd className="font-mono">{String(c.nfkc_casefold_match)}</dd></div>
                <div><dt className="text-muted">Hidden code points</dt><dd className="font-mono">{c.hidden_codepoints_in_original}</dd></div>
                <div><dt className="text-muted">Hidden recovered</dt><dd className="font-mono">{c.hidden_codepoints_recovered}</dd></div>
                <div><dt className="text-muted">Confidence / latency</dt><dd className="font-mono">{r.confidence?.toFixed(1) ?? "—"} · {r.latency_ms?.toFixed(0) ?? "—"} ms</dd></div>
              </dl>
            )}
            {Array.isArray(r.metadata?.missing_langs) && (r.metadata.missing_langs as string[]).length > 0 && (
              <p className="text-xs text-amber-600 dark:text-amber-300">Missing OCR language packs: {(r.metadata.missing_langs as string[]).join(", ")}</p>
            )}
          </>
        )}
      </div>
    </Card>
  );
}

export function MultimodalLab() {
  const [text, setText] = useState(SAMPLES.homoglyph ?? "");
  const [width, setWidth] = useState(900);
  const [fontSize, setFontSize] = useState(32);
  const run = useMutation<MultimodalResult, ApiError, void>({
    mutationFn: () => api.multimodal({ text, width, font_size: fontSize, run_ocr: true, run_vlm: true }),
  });
  const r = run.data;
  const imgSrc = r ? new URL(r.image_url.replace(/^\/api\/v1/, API_BASE), window.location.origin).toString() : null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Multimodal Laboratory</h1>
        <p className="mt-1 text-sm text-muted">Render text into a sandboxed screenshot, read it back with OCR and a vision-language model, and compare what each path sees.</p>
      </div>
      <Card>
        <CardHeader title={<label htmlFor="mm-input">Original text</label>} actions={<Badge tone={countInvisible(text) ? "amber" : "neutral"}>invisible: {countInvisible(text)}</Badge>} />
        <textarea id="mm-input" rows={2} value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} maxLength={2000} className="block w-full resize-y bg-transparent p-4 text-base outline-none" />
        <p className="border-t border-line px-4 py-2 font-mono text-xs break-all text-muted" aria-label="Original with invisible characters revealed">{revealInvisible(text)}</p>
        <div className="flex flex-wrap items-end gap-3 border-t border-line px-4 py-3">
          <span className="text-xs text-muted">Examples:</span>
          {Object.keys(SAMPLES).map((k) => (
            <button key={k} type="button" onClick={() => setText(SAMPLES[k] ?? "")} className="rounded border border-line px-2 py-0.5 font-mono text-xs text-muted hover:bg-surface-2 hover:text-fg">{k}</button>
          ))}
          <label className="ml-auto flex flex-col gap-1 text-xs text-muted">Width
            <input type="number" min={200} max={2000} value={width} onChange={(e) => setWidth(Number(e.target.value))} className="w-24 rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-sm" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">Font size
            <input type="number" min={10} max={96} value={fontSize} onChange={(e) => setFontSize(Number(e.target.value))} className="w-20 rounded-md border border-line bg-surface-2 px-2 py-1 font-mono text-sm" />
          </label>
          <Button variant="primary" onClick={() => run.mutate()} disabled={!text || run.isPending}>
            <ImageIcon className="size-3.5" /> {run.isPending ? "Rendering…" : "Render and read"}
          </Button>
        </div>
      </Card>
      {run.isError && <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm"><span className="font-mono text-red-500">{run.error.code}</span> {run.error.message}</p>}
      {!r && !run.isError && <Card className="p-8 text-center text-sm text-muted">Render a text to see its screenshot and every reading path side by side.</Card>}
      {r && imgSrc && (
        <>
          <Card>
            <CardHeader title="Rendered screenshot" actions={<span className="font-mono text-xs text-muted">{r.renderer} · {r.width}×{r.height}px</span>} />
            <div className="flex flex-col gap-3 p-4">
              <div className="overflow-x-auto rounded-md border border-line bg-white p-2"><img src={imgSrc} alt="Sandboxed rendering of the original text" width={r.width} height={r.height} className="max-w-none" data-testid="mm-image" /></div>
              <dl className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
                <div><dt className="text-muted">Image SHA-256</dt><dd className="font-mono break-all">{r.image_sha256}</dd></div>
                <div><dt className="text-muted">Browser · JavaScript · blocked requests</dt><dd className="font-mono">{String(r.provenance.browser)} · {String(r.provenance.javascript)} · {Array.isArray(r.provenance.network_requests_blocked) ? r.provenance.network_requests_blocked.length : 0}</dd></div>
              </dl>
              <details className="text-xs"><summary className="cursor-pointer text-muted">Rendering provenance</summary><pre className="mt-2 overflow-auto rounded bg-surface-2 p-2 font-mono">{JSON.stringify(r.provenance, null, 2)}</pre></details>
            </div>
          </Card>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="min-w-0">
              <CardHeader title="Text path" />
              <div className="flex flex-col gap-2 p-4 text-sm">
                <p className="rounded-md bg-surface-2 p-3 text-base break-words">{text}</p>
                <p className="text-xs text-muted">Models on the text path see every code point, including {countInvisible(text)} invisible one(s).</p>
                <Link to="/inspector" state={{ text }} className="text-xs text-violet-500 hover:underline">Inspect evidence in the Unicode Inspector →</Link>
              </div>
            </Card>
            {r.ocr && <ReadingCard title="OCR" icon={<ScanText className="size-4" />} r={r.ocr} />}
            {r.vlm && <ReadingCard title="VLM" icon={<Eye className="size-4" />} r={r.vlm} />}
          </div>
          <p className={clsx("text-xs text-muted")}>Grapheme error rate is measured against the visible form of the original (hidden code points removed). Single readings are observations, not research results.</p>
        </>
      )}
    </div>
  );
}
