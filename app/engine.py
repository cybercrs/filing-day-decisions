"""Pure scoring and summary logic for Filing Day Decisions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


METRIC_LABELS = {
    "usefulness": "Decision usefulness",
    "faithfulness": "Faithful representation",
    "comparability": "Comparability",
    "timeliness": "Timeliness",
    "confidence": "Reporting confidence",
}

STARTING_METRICS = {metric: 50 for metric in METRIC_LABELS}


def clamp(value: int, lower: int = 0, upper: int = 100) -> int:
    """Keep a score inside the inclusive display range."""
    return max(lower, min(upper, value))


def evaluate_question(question: Mapping[str, Any], selected_index: int) -> dict[str, Any]:
    """Return a serializable result for one selected answer."""
    options = question["options"]
    if not 0 <= selected_index < len(options):
        raise IndexError("Selected option is outside this question's answer choices.")

    selected = options[selected_index]
    correct_index = next(
        index for index, option in enumerate(options) if option.get("correct", False)
    )
    correct = options[correct_index]

    return {
        "question_id": question["id"],
        "prompt": question["prompt"],
        "concept": question["concept"],
        "selected_index": selected_index,
        "selected_text": selected["text"],
        "correct_index": correct_index,
        "correct_text": correct["text"],
        "is_correct": selected_index == correct_index,
        "feedback": selected["feedback"],
        "explanation": question["explanation"],
        "impacts": dict(selected["impacts"]),
    }


def apply_impacts(
    current: Mapping[str, int], impacts: Mapping[str, int]
) -> dict[str, int]:
    """Apply one decision's metric changes without exceeding 0–100."""
    updated = dict(current)
    for metric, change in impacts.items():
        if metric not in METRIC_LABELS:
            raise KeyError(f"Unknown reporting metric: {metric}")
        updated[metric] = clamp(updated.get(metric, 0) + change)
    return updated


def apply_results(
    current: Mapping[str, int], results: Iterable[Mapping[str, Any]]
) -> dict[str, int]:
    """Apply the metric impacts from a sequence of evaluated decisions."""
    updated, _ = apply_results_with_changes(current, results)
    return updated


def apply_results_with_changes(
    current: Mapping[str, int], results: Iterable[Mapping[str, Any]]
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """Apply results and trace the points actually gained and lost per metric."""
    updated = dict(current)
    changes = {
        metric: {"gained": 0, "lost": 0} for metric in METRIC_LABELS
    }
    for result in results:
        previous = dict(updated)
        updated = apply_impacts(updated, result["impacts"])
        for metric in METRIC_LABELS:
            difference = updated[metric] - previous[metric]
            if difference > 0:
                changes[metric]["gained"] += difference
            elif difference < 0:
                changes[metric]["lost"] += abs(difference)
    return updated, changes


def summarize_results(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Create the final accuracy and concept summary."""
    result_list = list(results)
    correct_count = sum(bool(result["is_correct"]) for result in result_list)
    total = len(result_list)
    percent = round((correct_count / total) * 100) if total else 0

    concept_totals: dict[str, dict[str, int]] = {}
    for result in result_list:
        concept = result["concept"]
        concept_totals.setdefault(concept, {"correct": 0, "total": 0})
        concept_totals[concept]["total"] += 1
        concept_totals[concept]["correct"] += int(bool(result["is_correct"]))

    strengths = [
        concept
        for concept, scores in concept_totals.items()
        if scores["correct"] == scores["total"]
    ]
    review = [
        concept
        for concept, scores in concept_totals.items()
        if scores["correct"] < scores["total"]
    ]

    if percent >= 85:
        status = "Filing ready"
        message = "Your report is useful, credible, and ready for a confident debrief."
    elif percent >= 65:
        status = "Promising draft"
        message = "The foundation is strong. A few reporting choices deserve another look."
    else:
        status = "Needs another pass"
        message = "Revisit the concepts below before releasing the report to users."

    return {
        "correct": correct_count,
        "total": total,
        "percent": percent,
        "status": status,
        "message": message,
        "strengths": strengths,
        "review": review,
        "concept_totals": concept_totals,
    }
