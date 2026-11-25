import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, CircleDashed, Moon, RefreshCw, Sun } from "lucide-react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import { Badge, Button, Card, CardHeader, Skeleton } from "../components/ui";
import { useTheme } from "../lib/theme";

const AVAIL_TONE: Record<string, "emerald" | "amber" | "red" | "neutral"> = {
  available: "emerald",
  not_downloaded: "amber",
  dependency_missing: "red",
  resources_insufficient: "red",
};

// Tesseract packs needed for the project's scripts (Latin, Devanagari, Gujarati).
const PROJECT_OCR: [string, string][] = [["eng", "Latin"], ["hin", "Devanagari"], ["guj", "Gujarati"]];

function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB"];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(1)} ${units[i]}`;
}

function Row({ k, children }: { k: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_minmax(0,1fr)] gap-3 px-4 py-2 text-sm sm:grid-cols-[12rem_minmax(0,1fr)]">
      <dt className="text-muted">{k}</dt>
      <dd className="min-w-0 break-words font-mono text-xs leading-5">{children}</dd>
    </div>
  );
}

function Ok({ ok }: { ok: boolean }) {
  return ok ? <CheckCircle2 className="size-4 shrink-0 text-emerald-500" aria-label="ok" /> : <CircleDashed className="size-4 shrink-0 text-amber-500" aria-label="not available" />;
}

export function Settings() {
  const { theme, toggle } = useTheme();
  const info = useQuery({ queryKey: ["system-info"], queryFn: api.systemInfo, retry: 1 });
  const d = info.data;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Settings and system</h1>
        <p className="mt-1 text-sm text-muted">Runtime facts reported by the API. No filesystem paths, hostnames or credentials are shown.</p>
      </div>

      <Card>
        <CardHeader title="Appearance" />
        <div className="flex flex-wrap items-center justify-between gap-3 p-4 text-sm">
          <p>Theme: <span className="font-mono">{theme}</span> <span className="text-muted">(stored in this browser only)</span></p>
          <Button onClick={toggle} aria-label={`Use ${theme === "dark" ? "light" : "dark"} theme`}>
            {theme === "dark" ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />} Use {theme === "dark" ? "light" : "dark"} theme
          </Button>
        </div>
      </Card>

      {info.isPending ? (
        <div className="flex flex-col gap-3" data-testid="settings-loading"><Skeleton className="h-40" /><Skeleton className="h-56" /></div>
      ) : info.isError || !d ? (
        <Card>
          <div role="alert" className="flex items-start gap-2 p-4 text-sm">
            <CircleAlert className="mt-0.5 size-4 shrink-0 text-red-500" />
            <div className="flex flex-col items-start gap-2">
              <p><span className="font-medium">System information unavailable.</span> <span className="text-muted">Start the API, then retry.</span></p>
              <Button onClick={() => void info.refetch()}><RefreshCw className="size-3.5" /> Retry</Button>
            </div>
          </div>
        </Card>
      ) : (
        <>
          {d.test_doubles_enabled && (
            <p data-testid="test-doubles-enabled" className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-700 dark:text-amber-300">
              Test doubles are enabled. Their outputs are labelled and are never research results.
            </p>
          )}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="Runtime" />
              <dl className="divide-y divide-line">
                <Row k="EmojiLens">{d.version}</Row>
                <Row k="Python">{d.python} on {d.platform}</Row>
                <Row k="Inference device">{d.device} <span className="font-sans text-muted">· {d.device_reason}</span></Row>
                {Object.entries(d.limits).map(([k, v]) => <Row key={k} k={k.replaceAll("_", " ")}>{k.endsWith("bytes") ? bytes(v) : v.toLocaleString()}</Row>)}
              </dl>
            </Card>
            <Card>
              <CardHeader title="Storage" actions={<Ok ok={d.database.ok} />} />
              <dl className="divide-y divide-line">
                <Row k="Database">{d.database.backend ?? "unknown"}{d.database.journal_mode ? ` · ${d.database.journal_mode}` : ""}</Row>
                <Row k="Schema">{d.database.error ? `error: ${d.database.error}` : `${d.database.migration ?? "none"} (head ${d.database.head ?? "?"})`}</Row>
                <Row k="Artifacts">{d.artifacts.files.toLocaleString()} files · {bytes(d.artifacts.bytes)}</Row>
                <Row k="OCR (project scripts)">
                  {d.ocr_languages.length ? (
                    <span className="flex flex-wrap gap-1.5" data-testid="ocr-project">
                      {PROJECT_OCR.map(([code, name]) => <Badge key={code} tone={d.ocr_languages.includes(code) ? "emerald" : "red"}>{code} {name} {d.ocr_languages.includes(code) ? "installed" : "missing"}</Badge>)}
                    </span>
                  ) : <span className="font-sans text-muted">Tesseract not found</span>}
                </Row>
                {d.ocr_languages.length > 0 && <Row k="OCR (all packs)">{d.ocr_languages.join(", ")}</Row>}
                <Row k="Renderer">{d.renderer.engine} · JS {d.renderer.javascript ? "on" : "off"} · network {d.renderer.network ? "on" : "off"}{d.renderer.playwright_installed ? "" : " · playwright missing"}</Row>
              </dl>
            </Card>
          </div>

          <Card>
            <CardHeader title="Models and pinned revisions" />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[34rem] text-left text-sm">
                <thead className="text-xs text-muted"><tr><th className="px-4 py-2 font-medium">Key</th><th className="px-2 py-2 font-medium">Task</th><th className="px-2 py-2 font-medium">Revision</th><th className="px-4 py-2 font-medium">Availability</th></tr></thead>
                <tbody className="divide-y divide-line">
                  {d.models.map((m) => (
                    <tr key={m.key}>
                      <td className="px-4 py-2"><span className="font-mono text-xs">{m.key}</span><span className="block truncate text-xs text-muted">{m.model_id}</span></td>
                      <td className="px-2 py-2 font-mono text-xs">{m.task}</td>
                      <td className="px-2 py-2 font-mono text-xs">{m.revision ? m.revision.slice(0, 12) : <span className="text-muted">not pinned</span>}</td>
                      <td className="px-4 py-2"><Badge tone={AVAIL_TONE[m.availability] ?? "neutral"}>{m.availability.replaceAll("_", " ")}</Badge>{m.test_double && <> <Badge tone="amber">TEST DOUBLE</Badge></>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <CardHeader title="Optional dependencies" />
            <ul className="divide-y divide-line">
              {d.dependencies.map((p) => (
                <li key={p.name} className="flex items-center gap-3 px-4 py-2 text-sm" data-testid={`dep-${p.name}`}>
                  <Ok ok={p.installed} />
                  <span className="font-mono text-xs">{p.name}</span>
                  <span className="min-w-0 flex-1 truncate text-xs text-muted">{p.purpose}</span>
                  <span className="font-mono text-xs text-muted">{p.installed ? (p.version ?? "installed") : "not installed"}</span>
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
