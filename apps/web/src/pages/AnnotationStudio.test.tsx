import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// Mocked API responses for UI tests only. No real annotation data.
const emptyAgreement = {
  field: "semantic_label", tasks_annotated: 0, tasks_with_two_or_more: 0, annotations: 0, alpha_nominal: null,
  pairwise_kappa: [], label_counts: {}, unsure_treated_as_missing: true, adjudicated: 0, note: "Labels entered by annotators only.",
};

function base() {
  server.use(
    http.get("*/api/v1/annotation/annotators", () => HttpResponse.json([{ pseudonym: "rater1", proficiency: {}, annotations: 0 }])),
    http.get("*/api/v1/annotation/agreement", () => HttpResponse.json(emptyAgreement)),
    http.get("*/api/v1/annotation/disagreements", () => HttpResponse.json([])),
    http.get("*/api/v1/annotation/guidelines", () => HttpResponse.json([])),
  );
}

describe("Annotation Studio", () => {
  it("shows undefined agreement honestly when there is no data", async () => {
    base();
    renderApp("/annotation");
    expect(await screen.findByTestId("alpha")).toHaveTextContent("undefined");
    expect(screen.getByText(/Select or register an annotator/)).toBeInTheDocument();
  });

  it("annotates a blinded queue item and requires both labels", async () => {
    base();
    let sent: unknown;
    let served = false;
    server.use(
      http.get("*/api/v1/annotation/queue", () =>
        HttpResponse.json(served ? null : { task_id: 3, guideline_version: "v1", language: "en", source_text: "good day", variant_text: "g\u043eod day", remaining: 1 }),
      ),
      http.post("*/api/v1/annotation/tasks/3/annotations", async ({ request }) => {
        sent = await request.json();
        served = true;
        return HttpResponse.json({ task_id: 3 }, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderApp("/annotation");
    await screen.findByRole("option", { name: /rater1/ });
    await user.selectOptions(screen.getByLabelText("Annotate as"), "rater1");
    expect(await screen.findByTestId("queue-variant")).toHaveTextContent("g\u043eod day");
    const submit = screen.getByRole("button", { name: /submit and next/i });
    expect(submit).toBeDisabled();
    await user.click(screen.getByLabelText(/Equivalent: same meaning/));
    await user.click(screen.getByLabelText("Safe"));
    await user.click(submit);
    expect(await screen.findByTestId("queue-empty")).toBeInTheDocument();
    expect(sent).toEqual({ annotator: "rater1", semantic_label: "equivalent", safety_label: "safe", note: "" });
  });
});
