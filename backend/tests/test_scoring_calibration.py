"""
Score calibration unit tests + a runnable validation report.

Run as pytest:
    cd backend && python -m pytest tests/test_scoring_calibration.py -v

Run standalone (prints the 15-value calibration table):
    cd backend && python tests/test_scoring_calibration.py
"""
import os
import sys

# Make `app` importable whether this file is run directly (script) or via pytest.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.score_calibration import (  # noqa: E402
    raw_to_100,
    compute_potential_score,
    anchor_categories,
    FLOOR,
    CAP,
)


# ── raw → 100 mapping ────────────────────────────────────────────────────────

def test_monotonic_non_decreasing():
    prev = -1.0
    for raw in [x / 100.0 for x in range(80, 490)]:
        score = raw_to_100(raw)
        assert score >= prev, f"non-monotonic at raw={raw}"
        prev = score


def test_floor_and_cap():
    assert raw_to_100(None) == FLOOR
    assert raw_to_100(0.0) == FLOOR
    assert raw_to_100(1.0) == FLOOR
    assert raw_to_100(4.6) == CAP
    assert raw_to_100(5.5) == CAP


def test_determinism():
    assert raw_to_100(3.14159) == raw_to_100(3.14159)
    assert compute_potential_score(61.3) == compute_potential_score(61.3)


def test_known_anchors():
    assert raw_to_100(2.0) == 52.0
    assert raw_to_100(2.6) == 63.0
    assert raw_to_100(3.2) == 74.0
    assert raw_to_100(3.8) == 84.0
    assert raw_to_100(4.3) == 91.0


# ── potential score ──────────────────────────────────────────────────────────

def test_potential_score_range_and_taper():
    for current in [30.0, 45.0, 55.0, 70.0, 84.0, 94.0]:
        p = compute_potential_score(current)
        assert p >= current, "potential must be >= current"
        assert p <= CAP, "potential must not exceed cap"
        assert p == round(current + (CAP - current) * 0.45, 1)

    assert compute_potential_score(None) is None


# ── category anchoring ───────────────────────────────────────────────────────

def test_anchor_preserves_ordering():
    raw = {"a": 90.0, "b": 60.0, "c": 45.0}
    anchored = anchor_categories(raw, overall=55.0)
    # relative ordering must be preserved
    assert anchored["a"] > anchored["b"] > anchored["c"]


def test_anchor_centers_on_overall():
    # Obama: old holistic 23.2 vs harmony 92.3 → now anchored to ~50
    raw = {
        "facial_harmony": 92.3,
        "skin_quality": 78.8,
        "jawline_definition": 66.0,
        "eye_appeal": 88.2,
        "facial_structure": 43.5,
        "masculinity_femininity": 60.4,
    }
    anchored = anchor_categories(raw, overall=50.4)
    mean = sum(anchored.values()) / len(anchored)
    # Clamping extreme categories to [FLOOR, CAP] can nudge the mean by a
    # point or two, but it must stay close to the holistic score.
    assert abs(mean - 50.4) < 2.5, f"anchored mean {mean} should be ~50.4"
    # harmony stays the best, structure the worst
    assert anchored["facial_harmony"] == max(anchored.values())
    assert anchored["facial_structure"] == min(anchored.values())
    # every category respects the same floor/cap as the overall score
    assert all(FLOOR <= v <= CAP for v in anchored.values())


def test_anchor_clamps_and_empty():
    assert anchor_categories({}, overall=50.0) == {}
    anchored = anchor_categories({"x": 200.0, "y": -50.0}, overall=50.0)
    assert anchored["x"] == CAP
    assert anchored["y"] == FLOOR


# ── standalone report ────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 74)
    print("SCORE CALIBRATION — 15-value validation (raw → new score)")
    print("=" * 74)

    # 6 real raw values reverse-engineered from the live matrix (old code
    # used score = (raw - 1) / 4 * 100, so raw = 1 + old_score / 25).
    real = [
        ("obama (real)", 1.928, 23.2),
        ("real_15", 2.428, 35.7),
        ("real_70", 3.528, 63.2),
        ("real_47", 3.728, 68.2),
        ("real_2 (A/B)", 3.740, 68.5),
        ("real_68", 3.860, 71.5),
    ]
    synthetic = [1.0, 1.5, 2.0, 2.3, 2.6, 3.0, 3.2, 4.3, 4.6]

    print(f"{'label':<16} {'raw':>7} {'old':>7} {'new':>7} {'potential':>10}")
    print("-" * 50)
    new_scores = []
    for label, raw, old in real:
        new = raw_to_100(raw)
        pot = compute_potential_score(new)
        new_scores.append(new)
        print(f"{label:<16} {raw:>7.3f} {old:>7.1f} {new:>7.1f} {pot:>10.1f}")
    print("-" * 50)
    for raw in synthetic:
        new = raw_to_100(raw)
        pot = compute_potential_score(new)
        new_scores.append(new)
        print(f"{'[synthetic]':<16} {raw:>7.3f} {'-':>7} {new:>7.1f} {pot:>10.1f}")

    new_scores.sort()
    n = len(new_scores)
    median = (new_scores[n // 2] + new_scores[n // 2 - 1]) / 2 if n % 2 == 0 else new_scores[n // 2]
    p90 = new_scores[int(n * 0.9) - 1]
    print("-" * 74)
    print(f"n={n}  min={new_scores[0]}  median={median}  P90={p90}  max={new_scores[-1]}")
    print(f"floor={FLOOR}  cap={CAP}")
    print("=" * 74 + "\n")

    # Quick sanity checks (fail loudly if anything regressed)
    test_monotonic_non_decreasing()
    test_floor_and_cap()
    test_determinism()
    test_known_anchors()
    test_potential_score_range_and_taper()
    test_anchor_preserves_ordering()
    test_anchor_centers_on_overall()
    test_anchor_clamps_and_empty()
    print("✅ All calibration assertions passed.\n")


if __name__ == "__main__":
    main()
