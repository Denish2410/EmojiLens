"""Inter-annotator agreement for nominal labels.

* Cohen's kappa for two raters on the same items: ``(p_o - p_e) / (1 - p_e)``.
* Krippendorff's alpha (nominal) for any number of raters with missing values:
  ``1 - D_o / D_e`` from the coincidence matrix, where units with fewer than two values
  are not pairable and are ignored.

Both return ``None`` when undefined (no pairable data, or zero expected disagreement), never a
made-up number. ``unsure`` labels are treated as missing by the callers (see the analysis plan).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Sequence

SEMANTIC_LABELS = ("equivalent", "partial", "not_equivalent", "unsure")
SAFETY_LABELS = ("safe", "unsafe", "unsure")


def cohen_kappa(pairs: Sequence[tuple[Hashable, Hashable]]) -> float | None:
    n = len(pairs)
    if n == 0:
        return None
    p_o = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    p_e = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    if p_e == 1.0:
        return None
    return (p_o - p_e) / (1 - p_e)


def krippendorff_alpha_nominal(units: Sequence[Sequence[Hashable]]) -> float | None:
    coincidence: dict[tuple[Hashable, Hashable], float] = {}
    for values in units:
        m = len(values)
        if m < 2:
            continue
        counts = Counter(values)
        for c, nc in counts.items():
            for k, nk in counts.items():
                pairs = nc * (nc - 1) if c == k else nc * nk
                if pairs:
                    coincidence[(c, k)] = coincidence.get((c, k), 0.0) + pairs / (m - 1)
    n_c: dict[Hashable, float] = {}
    for (c, _k), v in coincidence.items():
        n_c[c] = n_c.get(c, 0.0) + v
    n = sum(n_c.values())
    if n <= 1:
        return None
    d_o = sum(v for (c, k), v in coincidence.items() if c != k)
    d_e = sum(n_c[c] * n_c[k] for c in n_c for k in n_c if c != k) / (n - 1)
    if d_e == 0:
        return None
    return 1 - d_o / d_e
