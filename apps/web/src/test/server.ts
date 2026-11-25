// MSW handlers for component tests. These are mocked API responses used only in
// frontend unit tests; they are never shown to users or used as research data.
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

export const handlers = [
  http.get("*/api/v1/health", () => HttpResponse.json({ status: "ok", version: "0.1.0" })),
  http.get("*/api/v1/ready", () =>
    HttpResponse.json({
      status: "ready",
      checks: [
        { name: "database", ok: true, detail: "journal_mode=wal" },
        { name: "migrations", ok: true, detail: "current=0001 head=0001" },
      ],
    }),
  ),
  http.get("*/api/v1/dashboard/summary", () =>
    HttpResponse.json({
      datasets: { total: 0, by_kind: {}, versions: 0, frozen_versions: 0, sources: 0 },
      languages: {},
      transforms: { variants: 0, invalid_variants: 0, recipes: 0, families: [] },
      annotation: { annotators: 0, annotations: 0, adjudications: 0 },
      models: { catalogue: 5, test_doubles: 0, availability: { not_downloaded: 4, available: 1 } },
      experiments: { by_status: {}, outputs: 0, failed_outputs: 0, test_double_outputs: 0, reportable: 0 },
      crsc: { metric_rows: 0, experiments: 0 },
      multimodal: { render_artifacts: 0 },
      guard: { evaluations: 0, detector_artifacts: 0 },
      readiness: [{ key: "evaluation_dataset", label: "Frozen evaluation dataset", ok: false, detail: "0 frozen evaluation version(s)" }],
      reportable: false,
    }),
  ),
];

export const server = setupServer(...handlers);
