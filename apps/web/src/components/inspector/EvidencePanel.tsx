import clsx from "clsx";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { EVIDENCE_ORDER, type Evidence, type EvidenceCategory } from "../../api/types";
import { Badge, Card, CardHeader } from "../ui";

export const CATEGORY_META: Record<
  EvidenceCategory,
  { label: string; tone: "emerald" | "neutral" | "amber" | "red" | "violet" }
> = {
  legitimate_structure: { label: "Legitimate structure", tone: "emerald" },
  informational: { label: "Informational", tone: "neutral" },
  anomalous: { label: "Anomalous", tone: "amber" },
  suspicious: { label: "Suspicious", tone: "red" },
  concealed_payload_decoded: { label: "Concealed payload decoded", tone: "violet" },
};

export interface Selection {
  start: number;
  end: number;
  source: string;
}

export function EvidencePanel({
  evidence,
  selection,
  onSelect,
}: {
  evidence: Evidence[];
  selection: Selection | null;
  onSelect: (s: Selection | null) => void;
}) {
  const counts = EVIDENCE_ORDER.map((c) => [c, evidence.filter((e) => e.category === c).length] as const);
  const ordered = [...evidence].sort(
    (a, b) =>
      EVIDENCE_ORDER.indexOf(b.category) - EVIDENCE_ORDER.indexOf(a.category) ||
      a.span.cp_start - b.span.cp_start,
  );
  const concerning = evidence.some((e) => EVIDENCE_ORDER.indexOf(e.category) >= 2);

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            {concerning ? (
              <ShieldAlert className="size-4 text-amber-500" aria-hidden="true" />
            ) : (
              <ShieldCheck className="size-4 text-emerald-500" aria-hidden="true" />
            )}
            Evidence
          </span>
        }
        actions={
          <div className="flex flex-wrap justify-end gap-1">
            {counts
              .filter(([, n]) => n > 0)
              .map(([c, n]) => (
                <Badge key={c} tone={CATEGORY_META[c].tone}>
                  {CATEGORY_META[c].label}: {n}
                </Badge>
              ))}
          </div>
        }
      />
      {ordered.length === 0 ? (
        <p className="p-4 text-sm text-muted">
          No findings. The input contains no invisible, directional, styled or mixed-script
          structures.
        </p>
      ) : (
        <ul className="divide-y divide-line" aria-label="Evidence findings">
          {ordered.map((e) => {
            const active =
              selection?.source === e.id;
            const decoded = typeof e.details.decoded === "string" ? e.details.decoded : null;
            return (
              <li key={e.id}>
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() =>
                    onSelect(active ? null : { start: e.span.cp_start, end: e.span.cp_end, source: e.id })
                  }
                  className={clsx(
                    "flex w-full flex-col gap-1.5 px-4 py-3 text-left transition-colors hover:bg-surface-2",
                    active && "bg-violet-500/10",
                  )}
                >
                  <span className="flex flex-wrap items-center gap-2">
                    <Badge tone={CATEGORY_META[e.category].tone}>{CATEGORY_META[e.category].label}</Badge>
                    <code className="font-mono text-xs text-muted">{e.rule}</code>
                    <span className="ml-auto font-mono text-[11px] text-muted">
                      cp {e.span.cp_start}–{e.span.cp_end} · utf16 {e.span.utf16_start}–
                      {e.span.utf16_end}
                    </span>
                  </span>
                  <span className="text-sm">{e.message}</span>
                  {decoded !== null && (
                    <span className="rounded-md border border-violet-500/30 bg-violet-500/5 px-2 py-1 font-mono text-xs">
                      <span className="text-muted">decoded (displayed as text, never executed): </span>
                      <span data-testid="decoded-payload">{decoded}</span>
                    </span>
                  )}
                  {typeof e.details.skeleton === "string" && (
                    <span className="font-mono text-xs text-muted">
                      reads like: {e.details.skeleton}
                    </span>
                  )}
                  {typeof e.details.nfkc === "string" && (
                    <span className="font-mono text-xs text-muted">NFKC: {e.details.nfkc}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <p className="border-t border-line px-4 py-2 text-xs text-muted">
        Evidence describes structure, not intent. Decoded payloads are shown only as inert text.
      </p>
    </Card>
  );
}
