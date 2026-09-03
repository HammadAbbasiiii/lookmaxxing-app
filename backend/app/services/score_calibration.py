"""
Score calibration — single source of truth for mapping the ML model's raw
output (and anchoring category scores) onto a human-plausible 0–100 scale.

Why this exists
---------------
RankInfoNet ends in a *linear* ranking head (no sigmoid), so its raw output is
not natively a 0–100 score. The previous map ``(raw - 1) / 4 * 100`` assumed the
model spans the full 1–5 range, which it does not in practice — real faces
cluster in a narrow band, so everyone landed in an unnaturally harsh 5–85 band
(e.g. a clearly above-average face scored 23/100 while its landmark-based
category breakdown reported 92/100 harmony).

These helpers are *pure* (no numpy/torch/mediapipe imports) so they can be
unit-tested and reasoned about in isolation. They are deliberately monotonic
and deterministic: the same raw value always produces the same score.

Design targets (tune RAW_ANCHORS with live data — see below):
  - floor  ~30     (no humiliating lows for valid photos)
  - median ~55–60  (what users expect "average" to be)
  - P90    ~85–90
  - cap    ~95     (always leave a little room — honest and motivating)
"""
from typing import Dict, List, Tuple

# Piecewise-linear anchors: (raw_model_output, calibrated_0_100).
# Ordered ascending by raw value. Slopes decrease toward the top so the score
# approaches the cap with diminishing returns ("there's always room").
RAW_ANCHORS: List[Tuple[float, float]] = [
    (1.0, 30.0),  # floor — raw at/below this clamps to 30
    (2.0, 52.0),  # typical/average face
    (2.6, 63.0),  # above average
    (3.2, 74.0),  # good-looking
    (3.8, 84.0),  # very attractive
    (4.3, 91.0),  # excellent
    (4.6, 95.0),  # cap — raw at/above this clamps to 95
]

FLOOR: float = RAW_ANCHORS[0][1]   # 30.0
CAP: float = RAW_ANCHORS[-1][1]    # 95.0

# Potential score: how far toward the cap a user can realistically reach.
# 0.45 is the "credible optimism" slope — more headroom at the bottom,
# tapering toward the top so a 90 doesn't jump straight to 95+.
POTENTIAL_SLOPE: float = 0.45


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def raw_to_100(raw_score: float) -> float:
    """Monotonic piecewise-linear map from model raw output to a 0–100 score."""
    if raw_score is None:
        return FLOOR
    raw_score = float(raw_score)

    if raw_score <= RAW_ANCHORS[0][0]:
        return FLOOR
    if raw_score >= RAW_ANCHORS[-1][0]:
        return CAP

    for (r_lo, s_lo), (r_hi, s_hi) in zip(RAW_ANCHORS, RAW_ANCHORS[1:]):
        if r_lo <= raw_score <= r_hi:
            frac = (raw_score - r_lo) / (r_hi - r_lo)
            return round(s_lo + frac * (s_hi - s_lo), 1)

    return CAP  # defensive — unreachable given the checks above


def compute_potential_score(current: float) -> float:
    """Deterministic "achievable" score — credible optimism, tapering at the top."""
    if current is None:
        return None
    current = float(current)
    potential = current + (CAP - current) * POTENTIAL_SLOPE
    return round(min(CAP, potential), 1)


def anchor_categories(
    raw_scores: Dict[str, float],
    overall: float,
    spread: float = 1.0,
) -> Dict[str, float]:
    """Anchor category scores to the holistic score while preserving ordering.

    A linear shift (plus clamp) keeps each category's *relative* strength or
    weakness intact but re-centres the set on the holistic score, so the whole
    report stays coherent:

        anchored_i = clamp(overall + (raw_i - mean(raw)) * spread, 0, 100)

    ``spread`` damps (spread < 1) or amplifies (spread > 1) the relative
    differences. The default 1.0 preserves them exactly.
    """
    if not raw_scores:
        return {}

    overall = float(overall) if overall is not None else 50.0
    values = [float(v) for v in raw_scores.values()]
    mean = sum(values) / len(values)

    anchored: Dict[str, float] = {}
    for name, raw in raw_scores.items():
        anchored[name] = round(
            _clamp(overall + (float(raw) - mean) * spread, 0.0, 100.0), 1
        )
    return anchored
