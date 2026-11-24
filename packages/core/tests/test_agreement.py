from __future__ import annotations

import pytest

from emojilens_core.annotation import cohen_kappa, krippendorff_alpha_nominal


def test_cohen_kappa_hand_computed() -> None:
    # p_o = 0.75; p_e = 0.5*0.25 + 0.5*0.75 = 0.5; kappa = (0.75-0.5)/(1-0.5) = 0.5
    pairs = [("y", "y"), ("y", "n"), ("n", "n"), ("n", "n")]
    assert cohen_kappa(pairs) == pytest.approx(0.5)


def test_cohen_kappa_perfect_and_undefined() -> None:
    assert cohen_kappa([("a", "a"), ("b", "b")]) == pytest.approx(1.0)
    assert cohen_kappa([("a", "a"), ("a", "a")]) is None  # p_e == 1
    assert cohen_kappa([]) is None


def test_cohen_kappa_systematic_disagreement_is_negative() -> None:
    value = cohen_kappa([("a", "b"), ("b", "a")])
    assert value is not None
    assert value < 0


def test_krippendorff_alpha_hand_computed() -> None:
    # o_aa=2, o_ab=o_ba=1, o_bb=2; n_a=n_b=3, n=6; D_o=2; D_e=18/5; alpha=1-2/3.6
    assert krippendorff_alpha_nominal([["a", "a"], ["a", "b"], ["b", "b"]]) == pytest.approx(
        1 - 2 / 3.6
    )


def test_krippendorff_alpha_ignores_unpairable_units_and_handles_three_raters() -> None:
    units = [["a", "a", "a"], ["b", "b"], ["a"], [], ["b", "b", "b"]]
    assert krippendorff_alpha_nominal(units) == pytest.approx(1.0)


def test_krippendorff_alpha_undefined_cases() -> None:
    assert krippendorff_alpha_nominal([["a"], ["b"]]) is None
    assert krippendorff_alpha_nominal([["a", "a"], ["a", "a"]]) is None


def test_two_rater_alpha_close_to_kappa_for_large_samples() -> None:
    pairs = [("y", "y")] * 40 + [("y", "n")] * 10 + [("n", "y")] * 5 + [("n", "n")] * 45
    kappa = cohen_kappa(pairs)
    alpha = krippendorff_alpha_nominal([[a, b] for a, b in pairs])
    assert kappa is not None
    assert alpha is not None
    assert abs(kappa - alpha) < 0.02
