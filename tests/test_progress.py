"""Checks for refresh-safe progress snapshots and recovery."""

from __future__ import annotations

import unittest

from app.content import ROUNDS
from app.engine import STARTING_METRICS
from app.progress import (
    SNAPSHOT_VERSION,
    SnapshotError,
    create_option_order,
    decode_snapshot,
    encode_snapshot,
    hydrate_snapshot,
    new_activity_snapshot,
    validate_snapshot,
)


def mid_activity_snapshot(seed: int = 8675309) -> dict[str, object]:
    submitted_questions = [
        question
        for round_data in ROUNDS[:2]
        for question in round_data["questions"]
    ]
    current_question = ROUNDS[2]["questions"][0]
    submitted = {question["id"]: 0 for question in submitted_questions}
    choices = dict(submitted)
    choices[current_question["id"]] = 1
    return {
        "version": SNAPSHOT_VERSION,
        "page": "round",
        "round_index": 2,
        "round_submitted": False,
        "choices": choices,
        "results": submitted,
        "complete": False,
        "order_seed": seed,
        "revealed": [ROUNDS[0]["slug"]],
    }


class ProgressSnapshotTests(unittest.TestCase):
    def test_malformed_snapshots_are_rejected(self) -> None:
        with self.subTest("invalid encoding"):
            with self.assertRaises(SnapshotError):
                decode_snapshot("this-is-not-a-progress-token")

        with self.subTest("unsupported version"):
            snapshot = new_activity_snapshot(101)
            snapshot["version"] = 999
            with self.assertRaises(SnapshotError):
                validate_snapshot(snapshot)

        with self.subTest("incomplete submitted round"):
            snapshot = mid_activity_snapshot()
            first_question_id = ROUNDS[0]["questions"][0]["id"]
            del snapshot["results"][first_question_id]
            with self.assertRaises(SnapshotError):
                validate_snapshot(snapshot)

    def test_mid_activity_snapshot_restores_results_and_current_choice(self) -> None:
        original = mid_activity_snapshot()
        token = encode_snapshot(original)
        decoded = decode_snapshot(token)
        restored = hydrate_snapshot(decoded)

        current_question = ROUNDS[2]["questions"][0]
        expected_text = current_question["options"][1]["text"]
        self.assertEqual(restored["screen"], "round")
        self.assertEqual(restored["round_index"], 2)
        self.assertFalse(restored["round_submitted"])
        self.assertEqual(len(restored["responses"]), 6)
        self.assertEqual(
            restored["widget_answers"][f"answer-{current_question['id']}"],
            expected_text,
        )
        self.assertEqual(restored["option_order"], create_option_order(8675309))
        self.assertEqual(restored["saved_choices"], decoded["choices"])
        self.assertIn(ROUNDS[0]["slug"], restored["round_baselines"])
        self.assertIn(ROUNDS[1]["slug"], restored["round_baselines"])
        self.assertNotEqual(restored["metrics"], STARTING_METRICS)
        self.assertTrue(restored["revealed_answers"][ROUNDS[0]["slug"]])

    def test_start_over_replaces_prior_progress(self) -> None:
        prior_token = encode_snapshot(mid_activity_snapshot())
        replacement_token = encode_snapshot(new_activity_snapshot(2026))

        self.assertNotEqual(replacement_token, prior_token)
        replacement = decode_snapshot(replacement_token)
        restored = hydrate_snapshot(replacement)
        self.assertEqual(replacement["page"], "round")
        self.assertEqual(replacement["round_index"], 0)
        self.assertFalse(replacement["round_submitted"])
        self.assertFalse(replacement["complete"])
        self.assertEqual(replacement["choices"], {})
        self.assertEqual(replacement["results"], {})
        self.assertEqual(restored["responses"], [])
        self.assertEqual(restored["metrics"], STARTING_METRICS)


if __name__ == "__main__":
    unittest.main()
