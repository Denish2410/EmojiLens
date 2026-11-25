import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ShieldCheck, ShieldQuestion, ShieldX } from "lucide-react";
import { useState } from "react";
import { ApiError, api } from "../api/client";
import type { GuardAssessment } from "../api/types";
import { CATEGORY_META } from "../components/inspector/EvidencePanel";
import { Badge, Button, Card, CardHeader } from "../components/ui";
import { revealInvisible } from "../lib/visible";

const REC: Record<string, { label: string; tone: "emerald" | "neutral" | "amber" | "red"; icon: typeof ShieldCheck }> = {
  allow: { label: "Allow", tone: "emerald", icon: ShieldCheck },
  allow_with_information: { label: "Allow with information", tone: "emerald", icon: ShieldCheck },
  request_review: { label: "Request review", tone: "amber", icon: ShieldQuestion },
  flag_suspicious_transformation: { label: "Flag suspicious transformation", tone: "red", icon: ShieldX },
  block_by_policy: { label: "Block (policy)", tone: "red", icon: ShieldX },
};
const SWITCHES = ["rules", "detector", "decoders", "view_rescoring", "indic_aware"] as const;

function Gauge({ label, value, testid }: { label: string; value: number | null; testid: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-muted">{label}</span>
      <span className="font-mono text-2xl tabular-nums" data-testid={testid}>{value === null ? "—" : value.toFixed(3)}</span>
      <span className="h-1.5 rounded-full bg-surface-2"><span className="block h-1.5 rounded-full bg-violet-500/80" style={{ width: `${(value ?? 0) * 100}%` }} /></span>
    </div>
  );
}

export function GuardConsole() {
  const [text, setText] = useState("Reset your pass\u200bword at p\u0430ypal \u{1F44D}");
  const [ablation, setAblation] = useState<Record<string, boolean>>(Object.fromEntries(SWITCHES.map((s) => [s, true])));
  const [blockEnabled, setBlockEnabled] = useState(false);
  const [detectorId, setDetectorId] = useState<number | null>(null);
  const detectors = useQuery({ queryKey: ["detectors"], queryFn: api.detectors });
  const run = useMutation<GuardAssessment, ApiError, void>({
    mutationFn: () => api.assess({ text, ablation, policy: { block_enabled: blockEnabled }, detector_id: detectorId }),
  });
  const a = run.data;
  const rec = a ? REC[a.recommendation] ?? REC.allow! : null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">EmojiGuard Console</h1>
        <p className="mt-1 text-sm text-muted">Explainable assessment: located evidence, rule and detector contributions, uncertainty and a policy-based recommendation.</p>
      </div>
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card className="min-w-0">
          <CardHeader title={<label htmlFor="guard-input">Input</label>} />
          <textarea id="guard-input" rows={3} value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} className="block w-full resize-y bg-transparent p-4 text-base outline-none" />
          <p className="border-t border-line px-4 py-2 font-mono text-xs break-all text-muted">{revealInvisible(text)}</p>
        </Card>
        <Card className="min-w-0">
          <CardHeader title="Configuration" />
          <div className="flex flex-col gap-3 p-4 text-sm">
            <fieldset className="flex flex-col gap-1.5">
              <legend className="mb-1 text-xs text-muted">Components (ablation)</legend>
              {SWITCHES.map((s) => (
                <label key={s} className="flex items-center gap-2 font-mono text-xs"><input type="checkbox" checked={ablation[s]} onChange={(e) => setAblation({ ...ablation, [s]: e.target.checked })} />{s}</label>
              ))}
            </fieldset>
            <label className="flex flex-col gap-1 text-xs text-muted">Learned detector
              <select className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs" value={detectorId ?? ""} onChange={(e) => setDetectorId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">none (rules only)</option>
                {detectors.data?.map((d) => <option key={d.id} value={d.id}>#{d.id} {d.version}</option>)}
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={blockEnabled} onChange={(e) => setBlockEnabled(e.target.checked)} />Policy may block (off by default)</label>
            <Button variant="primary" onClick={() => run.mutate()} disabled={!text || run.isPending}>Assess</Button>
          </div>
        </Card>
      </div>
      {run.isError && <p role="alert" className="text-sm text-red-500">{run.error.code}: {run.error.message}</p>}
      {a && rec && (
        <>
          <Card>
            <div className="grid grid-cols-1 gap-6 p-5 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]">
              <div className="flex items-center gap-3">
                <rec.icon className={clsx("size-9", rec.tone === "emerald" ? "text-emerald-500" : rec.tone === "amber" ? "text-amber-500" : "text-red-500")} aria-hidden="true" />
                <div>
                  <p className="text-xs text-muted">Recommendation</p>
                  <p className="text-lg font-semibold" data-testid="guard-recommendation">{rec.label}</p>
                  <p className="text-xs text-muted">{a.uncertainty}</p>
                </div>
              </div>
              <Gauge label="Risk score (unvalidated)" value={a.risk_score} testid="guard-risk" />
              <Gauge label="Rule score" value={a.rule_score} testid="guard-rule" />
              <Gauge label="Detector score (uncalibrated)" value={a.detector_score} testid="guard-detector" />
            </div>
            <p className="border-t border-line px-5 py-2 font-mono text-[11px] text-muted">guard {a.guard_version} · {a.ablation} · {a.detector_version ?? "no detector"} · {a.latency_ms.toFixed(1)} ms · sha256 {a.input_sha256.slice(0, 16)}…</p>
          </Card>
          {a.notes.length > 0 && <ul className="text-xs text-amber-600 dark:text-amber-300">{a.notes.map((n) => <li key={n}>{n}</li>)}</ul>}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card className="min-w-0">
              <CardHeader title="Contributions" />
              {a.contributions.length === 0 ? <p className="p-4 text-sm text-muted">{a.explanation[0]}</p> : (
                <ul className="divide-y divide-line" aria-label="Contributions">
                  {[...a.contributions].sort((x, y) => y.weight - x.weight).map((c, i) => (
                    <li key={i} className="flex flex-col gap-1 px-4 py-3">
                      <div className="flex items-center gap-2"><Badge tone={c.source === "detector" ? "cyan" : c.source === "rule" ? "violet" : "amber"}>{c.source}</Badge><code className="font-mono text-xs">{c.name}</code><span className="ml-auto font-mono text-xs">{c.weight.toFixed(2)}</span></div>
                      <p className="text-xs text-muted">{c.detail}</p>
                      {c.evidence_ids.length > 0 && <p className="font-mono text-[10px] text-muted">{c.evidence_ids.join(", ")}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card className="min-w-0">
              <CardHeader title={`Evidence (${a.evidence.length})`} />
              <ul className="divide-y divide-line" aria-label="Guard evidence">
                {a.evidence.map((e) => {
                  const meta = CATEGORY_META[e.category as keyof typeof CATEGORY_META];
                  return (
                    <li key={e.id} className="flex flex-col gap-1 px-4 py-2 text-sm">
                      <div className="flex flex-wrap items-center gap-2"><Badge tone={meta?.tone ?? "neutral"}>{meta?.label ?? e.category}</Badge><code className="font-mono text-xs text-muted">{e.rule}</code><span className="ml-auto font-mono text-[11px] text-muted">cp {e.cp_start}–{e.cp_end}</span></div>
                      <p className="text-xs">{e.message}</p>
                    </li>
                  );
                })}
              </ul>
              {a.relevant_views.length > 0 && <p className="border-t border-line px-4 py-2 text-xs text-muted">Relevant derived views: {a.relevant_views.join(", ")}</p>}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
