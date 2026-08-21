"""Automated checks for scenario integrity and scoring behavior."""

from __future__ import annotations

import unittest

from app.content import ALL_QUESTIONS, ROUNDS
from app.engine import (
    METRIC_LABELS,
    STARTING_METRICS,
    apply_impacts,
    apply_results_with_changes,
    evaluate_question,
    summarize_results,
)


class ContentTests(unittest.TestCase):
    def test_six_rounds_cover_the_full_activity(self) -> None:
        self.assertEqual(len(ROUNDS), 6)
        self.assertEqual(len(ALL_QUESTIONS), 19)

    def test_question_ids_are_unique(self) -> None:
        question_ids = [question["id"] for question in ALL_QUESTIONS]
        self.assertEqual(len(question_ids), len(set(question_ids)))

    def test_every_question_has_exactly_one_correct_choice(self) -> None:
        for question in ALL_QUESTIONS:
            with self.subTest(question=question["id"]):
                correct_count = sum(
                    bool(option["correct"]) for option in question["options"]
                )
                self.assertEqual(correct_count, 1)

    def test_answer_texts_are_unique_within_each_question(self) -> None:
        for question in ALL_QUESTIONS:
            with self.subTest(question=question["id"]):
                answer_texts = [answer["text"] for answer in question["options"]]
                self.assertEqual(len(answer_texts), len(set(answer_texts)))

    def test_all_metric_impacts_use_known_metrics(self) -> None:
        for question in ALL_QUESTIONS:
            for answer in question["options"]:
                with self.subTest(question=question["id"], answer=answer["text"]):
                    self.assertTrue(set(answer["impacts"]).issubset(METRIC_LABELS))

    def test_every_round_has_a_student_reflection_and_answer(self) -> None:
        for round_data in ROUNDS:
            with self.subTest(round=round_data["slug"]):
                self.assertTrue(round_data["reflection_question"].strip())
                self.assertTrue(round_data["reflection_answer"].strip())

    def test_faithful_representation_uses_paired_evidence(self) -> None:
        faithful_round = next(
            round_data for round_data in ROUNDS if round_data["slug"] == "faithful"
        )
        for question in faithful_round["questions"]:
            with self.subTest(question=question["id"]):
                self.assertTrue(question["draft_paragraph"].strip())
                self.assertGreaterEqual(len(question["draft_paragraph"].split()), 20)
                self.assertTrue(question["fact"].strip())

class EngineTests(unittest.TestCase):
    def test_correct_choice_is_evaluated_and_serialized(self) -> None:
        question = ALL_QUESTIONS[0]
        correct_index = next(
            index for index, answer in enumerate(question["options"]) if answer["correct"]
        )
        result = evaluate_question(question, correct_index)
        self.assertTrue(result["is_correct"])
        self.assertEqual(result["question_id"], question["id"])
        self.assertEqual(result["correct_text"], result["selected_text"])

    def test_impacts_are_clamped_to_display_range(self) -> None:
        updated = apply_impacts(
            STARTING_METRICS,
            {"usefulness": 500, "faithfulness": -500},
        )
        self.assertEqual(updated["usefulness"], 100)
        self.assertEqual(updated["faithfulness"], 0)

    def test_metric_change_trace_separates_gains_and_losses(self) -> None:
        results = [
            {"impacts": {"usefulness": 8, "confidence": -3}},
            {"impacts": {"usefulness": -2, "confidence": 7}},
        ]
        updated, changes = apply_results_with_changes(STARTING_METRICS, results)
        self.assertEqual(updated["usefulness"], 56)
        self.assertEqual(changes["usefulness"], {"gained": 8, "lost": 2})
        self.assertEqual(updated["confidence"], 54)
        self.assertEqual(changes["confidence"], {"gained": 7, "lost": 3})

    def test_perfect_summary_is_filing_ready(self) -> None:
        results = []
        for question in ALL_QUESTIONS:
            correct_index = next(
                index
                for index, answer in enumerate(question["options"])
                if answer["correct"]
            )
            results.append(evaluate_question(question, correct_index))

        summary = summarize_results(results)
        self.assertEqual(summary["correct"], len(ALL_QUESTIONS))
        self.assertEqual(summary["percent"], 100)
        self.assertEqual(summary["status"], "Filing ready")
        self.assertFalse(summary["review"])

    def test_empty_summary_is_safe(self) -> None:
        summary = summarize_results([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["percent"], 0)


if __name__ == "__main__":
    unittest.main()
