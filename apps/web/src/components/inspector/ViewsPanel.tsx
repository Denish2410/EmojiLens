import clsx from "clsx";
import { Copy } from "lucide-react";
import { useState } from "react";
import type { DerivedView, ViewName } from "../../api/types";
import { copyText } from "../../lib/clipboard";
import { useToast } from "../Toast";
import { Badge, Card, CardHeader } from "../ui";
import type { Selection } from "./EvidencePanel";

const LABEL: Record<ViewName, string> = {
  original: "Original",
  nfc: "NFC",
  nfkc: "NFKC",
  sanitized: "Sanitized",
  demojized: "Demojized",
  decoded: "Decoded",
};

/** Shows each derived view with changed segments highlighted and traceable to the original. */
export function ViewsPanel({
  original,
  views,
  selection,
  onSelect,
}: {
  original: string;
  views: DerivedView[];
  selection: Selection | null;
  onSelect: (s: Selection | null) => void;
}) {
  const [active, setActive] = useState<ViewName>("sanitized");
  const toast = useToast();
  const view = views.find((v) => v.name === active) ?? views[0];
  if (!view) return null;
  // Slice the original by code point offsets (segment offsets are code points).
  const cps = Array.from(original);

  return (
    <Card>
      <CardHeader
        title="Derived views"
        actions={
          <button
            type="button"
            aria-label={`Copy ${LABEL[view.name]} view`}
            onClick={() =>
              void copyText(view.text).then((ok) =>
                toast(ok ? `${LABEL[view.name]} view copied` : "Clipboard unavailable", ok ? "ok" : "error"),
              )
            }
            className="rounded p-1 text-muted hover:bg-surface-2"
          >
            <Copy className="size-3.5" />
          </button>
        }
      />
      <div role="tablist" aria-label="Derived views" className="flex flex-wrap gap-1 border-b border-line px-3 pt-2">
        {views.map((v) => (
          <button
            key={v.name}
            type="button"
            role="tab"
            id={`view-tab-${v.name}`}
            aria-selected={v.name === view.name}
            aria-controls="view-panel"
            onClick={() => setActive(v.name)}
            className={clsx(
              "-mb-px flex items-center gap-1.5 border-b-2 px-2.5 py-1.5 text-sm",
              v.name === view.name
                ? "border-violet-500 text-fg"
                : "border-transparent text-muted hover:text-fg",
            )}
          >
            {LABEL[v.name]}
            {v.changed && <span className="size-1.5 rounded-full bg-cyan-400" aria-label="changed" />}
          </button>
        ))}
      </div>
      <div id="view-panel" role="tabpanel" aria-labelledby={`view-tab-${view.name}`} className="p-4">
        <p className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted">
          {view.description}
          <Badge tone={view.changed ? "cyan" : "neutral"}>{view.changed ? "differs from original" : "identical"}</Badge>
        </p>
        <div
          data-testid="view-text"
          className="rounded-md border border-line bg-surface-2 p-3 text-base break-words whitespace-pre-wrap"
        >
          {view.segments.map((seg, i) => {
            const orig = cps.slice(seg.original.cp_start, seg.original.cp_end).join("");
            const changed = orig !== seg.text;
            const selected =
              selection !== null &&
              seg.original.cp_start < selection.end &&
              seg.original.cp_end > selection.start;
            if (!changed && !selected) return <span key={i}>{seg.text}</span>;
            return (
              <button
                key={i}
                type="button"
                title={`original cp ${seg.original.cp_start}–${seg.original.cp_end}`}
                aria-label={seg.text === "" ? "removed characters" : undefined}
                onClick={() =>
                  onSelect({ start: seg.original.cp_start, end: seg.original.cp_end, source: `view:${view.name}:${i}` })
                }
                className={clsx(
                  "rounded px-0.5",
                  selected ? "bg-violet-500/25" : "bg-cyan-500/15",
                  seg.text === "" && "inline-block min-w-2 border-l-2 border-red-400 align-middle",
                )}
              >
                {seg.text}
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-muted">
          Highlighted segments differ from the original; click one to locate its source code points.
          A red bar marks removed characters.
        </p>
      </div>
    </Card>
  );
}
