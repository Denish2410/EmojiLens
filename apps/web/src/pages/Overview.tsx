import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, CircleAlert, RefreshCw } from "lucide-react";
import { Link } from "react-router";
import { api } from "../api/client";
import { Button, Card, CardHeader, Skeleton } from "../components/ui";

export function Overview() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, retry: 1 });
  const ready = useQuery({ queryKey: ["ready"], queryFn: api.ready, retry: 1 });
  const failed = health.isError || ready.isError;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Research overview</h1>
        <p className="mt-1 text-sm text-muted">
          See what AI sees. Detect what humans miss.
        </p>
      </div>

      <Card>
        <CardHeader
          title="System status"
          actions={
            <Button
              onClick={() => {
                void health.refetch();
                void ready.refetch();
              }}
              aria-label="Refresh system status"
            >
              <RefreshCw className="size-3.5" /> Refresh
            </Button>
          }
        />
        <div className="p-4">
          {health.isPending || ready.isPending ? (
            <div className="flex flex-col gap-2" data-testid="status-loading">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-5 w-64" />
            </div>
          ) : failed ? (
            <div className="flex items-start gap-2 text-sm text-red-500">
              <CircleAlert className="mt-0.5 size-4 shrink-0" />
              <div>
                <p className="font-medium">API unreachable</p>
                <p className="text-muted">
                  Start the API with <code className="font-mono">scripts/dev-api.sh</code>, then
                  refresh.
                </p>
              </div>
            </div>
          ) : (
            <ul className="flex flex-col gap-2 text-sm">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
                API {health.data?.version} is live
              </li>
              {ready.data?.checks.map((c) => (
                <li key={c.name} className="flex items-center gap-2">
                  {c.ok ? (
                    <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
                  ) : (
                    <CircleAlert className="size-4 shrink-0 text-amber-500" />
                  )}
                  <span className="capitalize">{c.name}</span>
                  <span className="font-mono text-xs text-muted">{c.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Research data" />
        <div className="flex flex-col items-start gap-3 p-4 text-sm">
          <p className="text-muted">
            No datasets or experiments exist yet. Dataset import and the experiment runner arrive
            in later milestones (see ROADMAP.md). Metrics appear here only once real experiments
            have been run.
          </p>
          <Link
            to="/inspector"
            className="inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 font-medium text-white hover:bg-violet-500"
          >
            Inspect Unicode input <ArrowRight className="size-3.5" />
          </Link>
        </div>
      </Card>
    </div>
  );
}
