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
];

export const server = setupServer(...handlers);
