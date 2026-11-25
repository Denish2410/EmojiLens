import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { Languages } from "lucide-react";
import { useState } from "react";
import { ApiError, api } from "../api/client";
import type { MultilingualResult } from "../api/types";
import { Distribution } from "../components/Distribution";
import { Badge, Button, Card, CardHeader } from "../components/ui";

// Short illustrative inputs (written for this UI), one per variety.
const SAMPLES: Record<string, string> = {
  en: "Are you coming to the party tonight? 🎉",
  hi: "आज मौसम बहुत अच्छा है 😊",
  gu: "આજે હવામાન ખૂબ સરસ છે 🌞",
  "hi-Latn": "kal milte hain, tum kya kar rahe ho? 👍",
  "gu-Latn": "tame kem cho? hu majama chhu 🙏",
  mixed: "aaj मौसम bahut अच्छा hai 😊",
};

const TAG_STYLE: Record<string, string> = {
  en: "border-sky-500/40 bg-sky-500/10",
  hi: "border-orange-500/40 bg-orange-500/10",
  gu: "border-emerald-500/40 bg-emerald-500/10",
  "hi-Latn": "border-amber-500/40 bg-amber-500/10",
  "gu-Latn": "border-teal-500/40 bg-teal-500/10",
  ambiguous: "border-dashed border-line",
  unknown: "border-line text-muted",
  emoji: "border-violet-500/40 bg-violet-500/10",
  other: "border-line text-muted",
};

export function MultilingualLab() {
  const [text, setText] = useState(SAMPLES.mixed ?? "");
  const varieties = useQuery({ queryKey: ["varieties"], queryFn: api.varieties });
  const m = useMutation<MultilingualResult, ApiError, string>({ mutationFn: api.multilingual });
  const r = m.data;
  const varietyName = (code: string) => varieties.data?.find((v) => v.code === code)?.name ?? code;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Multilingual Laboratory</h1>
        <p className="mt-1 text-sm text-muted">
          Language-variety identification, script analysis, code-mixing and localised emoji meanings
          for English, Hindi, Gujarati, Hinglish and Romanized Gujarati.
        </p>
      </div>

      <Card>
        <CardHeader
          title={<label htmlFor="ml-input">Text</label>}
          actions={
            <Button variant="primary" onClick={() => m.mutate(text)} disabled={m.isPending}>
              <Languages className="size-3.5" />
              {m.isPending ? "Analysing…" : "Analyse"}
            </Button>
          }
        />
        <textarea
          id="ml-input"
          rows={3}
          value={text}
          spellCheck={false}
          onChange={(e) => setText(e.target.value)}
          className="block w-full resize-y bg-transparent p-4 text-base outline-none"
        />
        <div className="flex flex-wrap items-center gap-1.5 border-t border-line px-4 py-2">
          <span className="text-xs text-muted">Examples:</span>
          {Object.entries(SAMPLES).map(([k, v]) => (
            <button
              key={k}
              type="button"
              onClick={() => setText(v)}
              className="rounded border border-line px-2 py-0.5 font-mono text-xs text-muted hover:bg-surface-2 hover:text-fg"
            >
              {k}
            </button>
          ))}
        </div>
      </Card>

      {m.isError && (
        <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm">
          <span className="font-mono text-red-500">{m.error.code}</span> {m.error.message}
        </div>
      )}

      {r && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader
                title="Identification"
                actions={<code className="font-mono text-[11px] text-muted">{r.identification.method}</code>}
              />
              <div className="flex flex-col gap-4 p-4">
                <div className="flex flex-wrap items-baseline gap-3">
                  <span className="text-2xl font-semibold" data-testid="variety-label">
                    {r.identification.label ? varietyName(r.identification.label) : "Undetermined"}
                  </span>
                  {r.identification.label && (
                    <span className="font-mono text-sm text-muted">
                      {r.identification.label} · confidence {r.identification.confidence.toFixed(2)}
                    </span>
                  )}
                  <Badge tone={r.identification.uncertain ? "amber" : "emerald"}>
                    {r.identification.uncertain ? "uncertain" : "clear evidence"}
                  </Badge>
                </div>
                {r.identification.reasons.length > 0 && (
                  <ul className="list-disc pl-5 text-xs text-muted" aria-label="Uncertainty reasons">
                    {r.identification.reasons.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                )}
                <Distribution title="Evidence mass by variety" data={r.identification.scores} />
                <dl className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <dt className="text-xs text-muted">Code-mixed</dt>
                    <dd className="font-mono">{r.identification.code_mixed ? "yes" : "no"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">CMI</dt>
                    <dd className="font-mono">{r.identification.cmi}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Switch points</dt>
                    <dd className="font-mono">{r.identification.switch_points}</dd>
                  </div>
                </dl>
                <p className="text-xs text-muted">
                  Heuristic baseline (script + seed lexicons). Code-mixing is normal language use and
                  never counts as a risk signal.
                </p>
              </div>
            </Card>
            <Card>
              <CardHeader title="Scripts" />
              <div className="p-4">
                <Distribution title="Letters by script" data={r.scripts} tone="cyan" />
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader title="Token tags" />
            <ul className="flex flex-wrap gap-1.5 p-4" aria-label="Token tags">
              {r.tokens.map((t) => (
                <li
                  key={`${t.cp_start}-${t.cp_end}`}
                  className={clsx("flex flex-col items-center rounded-md border px-2 py-1", TAG_STYLE[t.tag])}
                  title={t.candidates.length ? `candidates: ${t.candidates.join(", ")}` : t.tag}
                >
                  <span className="text-base">{t.text}</span>
                  <span className="font-mono text-[10px] text-muted">{t.tag}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <CardHeader title={`Emoji meanings (Unicode CLDR ${r.cldr_version})`} />
            {r.emoji.length === 0 ? (
              <p className="p-4 text-sm text-muted">No emoji in this text.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs text-muted">
                    <tr className="border-b border-line">
                      <th scope="col" className="px-3 py-2 font-medium">Emoji</th>
                      {["en", "hi", "gu", "hi-Latn", "gu-Latn"].map((v) => (
                        <th key={v} scope="col" className="px-3 py-2 font-mono font-medium">{v}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {r.emoji.map((e) => (
                      <tr key={e.cp_start} className="border-b border-line/60 align-top">
                        <td className="px-3 py-2 text-xl">{e.emoji}</td>
                        {["en", "hi", "gu", "hi-Latn", "gu-Latn"].map((v) => {
                          const mm = e.meanings.find((x) => x.variety === v);
                          return (
                            <td key={v} className="px-3 py-2">
                              {mm ? (
                                <span className="flex flex-col gap-0.5">
                                  <span>{mm.name}</span>
                                  {mm.fallback && (
                                    <span className="font-mono text-[10px] text-amber-600 dark:text-amber-300">
                                      fallback: {mm.locale}
                                    </span>
                                  )}
                                </span>
                              ) : (
                                <span className="text-muted">—</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
