# Results section template

Each paragraph is built only from the generated research report (`scripts/generate_report.py`) for
eligible runs. Fill each bracketed field from the report. Never type a number from memory.

**<Hypothesis id>: <statement>.** On <dataset slug> v<version> (<n groups> source groups, test split),
<model key>@<revision> gave <metric> = <value> (95% group-bootstrap CI [<low>, <high>], B = <B>) for
<condition A> versus <value> [<low>, <high>] for <condition B>. The difference was <diff> [<low>, <high>],
so the decision rule in the analysis plan was <met / not met>. Missing or errored pairs:
<count> (<share>), excluded. Run #<id>, outputs digest `<sha256>`.

**Exploratory strata.** <Variety / family / modality> results with at least 30 groups, labelled
exploratory, without p-values.

**Limitations specific to this result.** <coverage, annotation status, model size>.
