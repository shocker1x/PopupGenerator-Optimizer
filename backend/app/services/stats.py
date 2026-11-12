import hashlib
import random
from collections.abc import Sequence
from typing import Any

DEFAULT_MIN_IMPRESSIONS = 100
DEFAULT_WINNER_PROBABILITY = 0.95
DEFAULT_SIMULATIONS = 20_000


def _percentile(sorted_values: list[float], percentile: float) -> float:
    index = (len(sorted_values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def compare_variants(
    variants: Sequence[dict[str, Any]],
    campaign_id: str,
    default_version_id: str | None,
    min_impressions: int = DEFAULT_MIN_IMPRESSIONS,
    winner_probability_threshold: float = DEFAULT_WINNER_PROBABILITY,
    simulations: int = DEFAULT_SIMULATIONS,
) -> dict[str, Any]:
    if not variants:
        raise ValueError("At least one variant is required")
    if not 0 < winner_probability_threshold <= 1:
        raise ValueError("Winner probability threshold must be between 0 and 1")
    if simulations < 1:
        raise ValueError("At least one simulation is required")

    normalized: list[dict[str, Any]] = []
    for variant in variants:
        impressions = int(variant["impressions"])
        submissions = int(variant["submissions"])
        if impressions < 0 or submissions < 0 or submissions > impressions:
            raise ValueError("Submissions must be between zero and impressions")
        normalized.append({**variant, "impressions": impressions, "submissions": submissions})

    seed_source = f"{campaign_id}:" + ":".join(
        f"{item.get('version_id')}:{item['impressions']}:{item['submissions']}"
        for item in normalized
    )
    seed = int.from_bytes(hashlib.sha256(seed_source.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    samples: list[list[float]] = []
    for variant in normalized:
        alpha = 1 + variant["submissions"]
        beta = 1 + variant["impressions"] - variant["submissions"]
        samples.append([rng.betavariate(alpha, beta) for _ in range(simulations)])

    win_counts = [0] * len(normalized)
    for sample_index in range(simulations):
        best_index = max(
            range(len(normalized)),
            key=lambda index: samples[index][sample_index],
        )
        win_counts[best_index] += 1

    comparisons: list[dict[str, Any]] = []
    for index, variant in enumerate(normalized):
        sorted_samples = sorted(samples[index])
        comparisons.append(
            {
                "version_id": variant["version_id"],
                "label": variant["label"],
                "impressions": variant["impressions"],
                "submissions": variant["submissions"],
                "conversion_rate": (
                    round(variant["submissions"] / variant["impressions"] * 100, 2)
                    if variant["impressions"]
                    else 0.0
                ),
                "credible_interval_90": [
                    round(_percentile(sorted_samples, 0.05) * 100, 2),
                    round(_percentile(sorted_samples, 0.95) * 100, 2),
                ],
                "probability_best": round(win_counts[index] / simulations, 4),
            }
        )

    best_index = max(range(len(comparisons)), key=lambda index: comparisons[index]["probability_best"])
    best = comparisons[best_index]
    enough_data = all(item["impressions"] >= min_impressions for item in comparisons)
    confident = best["probability_best"] >= winner_probability_threshold
    current_default_index = next(
        (
            index
            for index, item in enumerate(comparisons)
            if str(item["version_id"]) == str(default_version_id)
        ),
        None,
    )
    expected_lift_percent = None
    if current_default_index is not None and current_default_index != best_index:
        baseline_mean = sum(samples[current_default_index]) / simulations
        best_mean = sum(samples[best_index]) / simulations
        expected_lift_percent = round((best_mean / baseline_mean - 1) * 100, 2)
    elif current_default_index == best_index:
        expected_lift_percent = 0.0

    if not enough_data:
        decision = "not_enough_data"
        winner_version_id = None
        message = "Not enough data yet. Each version needs at least 100 impressions."
    elif not confident:
        decision = "no_clear_winner"
        winner_version_id = None
        message = "No clear winner yet. Keep collecting impressions."
    else:
        decision = "winner"
        winner_version_id = best["version_id"]
        message = (
            f"Variant {best['label']} is most likely to perform best "
            f"({best['probability_best']:.0%} probability)."
        )

    return {
        "decision": decision,
        "message": message,
        "winner_version_id": winner_version_id,
        "winner_probability": best["probability_best"],
        "expected_lift_percent": expected_lift_percent,
        "min_impressions_per_version": min_impressions,
        "probability_threshold": winner_probability_threshold,
        "versions": comparisons,
    }