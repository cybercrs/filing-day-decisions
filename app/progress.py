"""Compact, validated progress snapshots for refresh-safe activity recovery."""

from __future__ import annotations

import base64
import binascii
import json
import random
import zlib
from collections.abc import Mapping
from typing import Any

from app.content import ROUNDS
from app.engine import STARTING_METRICS, apply_results, evaluate_question


QUERY_PARAM_NAME = "progress"
SNAPSHOT_VERSION = 1
MAX_TOKEN_LENGTH = 4096
MAX_JSON_BYTES = 8192
MAX_ORDER_SEED = (2**32) - 1

PAGE_TO_CODE = {"welcome": "w", "round": "r", "debrief": "d"}
CODE_TO_PAGE = {code: page for page, code in PAGE_TO_CODE.items()}

QUESTION_RECORDS = [
    (round_index, question)
    for round_index, round_data in enumerate(ROUNDS)
    for question in round_data["questions"]
]
QUESTION_BY_ID = {question["id"]: question for _, question in QUESTION_RECORDS}
QUESTION_INDEX_BY_ID = {
    question["id"]: index for index, (_, question) in enumerate(QUESTION_RECORDS)
}
ROUND_QUESTION_IDS = [
    [question["id"] for question in round_data["questions"]]
    for round_data in ROUNDS
]
ROUND_INDEX_BY_SLUG = {
    round_data["slug"]: index for index, round_data in enumerate(ROUNDS)
}


class SnapshotError(ValueError):
    """Raised when a progress token is malformed or internally inconsistent."""


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def create_option_order(seed: int) -> dict[str, list[int]]:
    """Create a stable randomized option order for one activity attempt."""
    if not _is_int(seed) or not 0 <= seed <= MAX_ORDER_SEED:
        raise SnapshotError("The option-order seed is invalid.")
    rng = random.Random(seed)
    return {
        question["id"]: rng.sample(
            range(len(question["options"])), k=len(question["options"])
        )
        for _, question in QUESTION_RECORDS
    }


def welcome_snapshot(seed: int) -> dict[str, Any]:
    """Return a clean snapshot for the activity introduction."""
    return {
        "version": SNAPSHOT_VERSION,
        "page": "welcome",
        "round_index": 0,
        "round_submitted": False,
        "choices": {},
        "results": {},
        "complete": False,
        "order_seed": seed,
        "revealed": [],
    }


def new_activity_snapshot(seed: int) -> dict[str, Any]:
    """Return the replacement state used by Begin and Start over."""
    snapshot = welcome_snapshot(seed)
    snapshot["page"] = "round"
    return snapshot


def _validate_choice_map(value: object, label: str) -> dict[str, int]:
    if not isinstance(value, Mapping) or len(value) > len(QUESTION_RECORDS):
        raise SnapshotError(f"The snapshot {label} are invalid.")

    validated: dict[str, int] = {}
    for question_id, option_index in value.items():
        if not isinstance(question_id, str) or question_id not in QUESTION_BY_ID:
            raise SnapshotError(f"The snapshot {label} reference an unknown question.")
        if not _is_int(option_index):
            raise SnapshotError(f"The snapshot {label} contain an invalid option.")
        question = QUESTION_BY_ID[question_id]
        if not 0 <= option_index < len(question["options"]):
            raise SnapshotError(f"The snapshot {label} contain an invalid option.")
        validated[question_id] = option_index
    return validated


def validate_snapshot(snapshot: object) -> dict[str, Any]:
    """Validate and normalize an expanded progress snapshot."""
    required = {
        "version",
        "page",
        "round_index",
        "round_submitted",
        "choices",
        "results",
        "complete",
        "order_seed",
        "revealed",
    }
    if not isinstance(snapshot, Mapping) or set(snapshot) != required:
        raise SnapshotError("The snapshot structure is invalid.")
    if snapshot["version"] != SNAPSHOT_VERSION:
        raise SnapshotError("The snapshot version is not supported.")

    page = snapshot["page"]
    if page not in PAGE_TO_CODE:
        raise SnapshotError("The snapshot page is invalid.")

    round_index = snapshot["round_index"]
    if not _is_int(round_index) or not 0 <= round_index < len(ROUNDS):
        raise SnapshotError("The snapshot round is invalid.")

    round_submitted = snapshot["round_submitted"]
    complete = snapshot["complete"]
    if not isinstance(round_submitted, bool) or not isinstance(complete, bool):
        raise SnapshotError("The snapshot status is invalid.")

    order_seed = snapshot["order_seed"]
    if not _is_int(order_seed) or not 0 <= order_seed <= MAX_ORDER_SEED:
        raise SnapshotError("The snapshot option-order seed is invalid.")

    choices = _validate_choice_map(snapshot["choices"], "choices")
    results = _validate_choice_map(snapshot["results"], "results")

    revealed = snapshot["revealed"]
    if (
        not isinstance(revealed, list)
        or any(not isinstance(slug, str) for slug in revealed)
        or len(revealed) != len(set(revealed))
    ):
        raise SnapshotError("The snapshot revealed answers are invalid.")
    if any(slug not in ROUND_INDEX_BY_SLUG for slug in revealed):
        raise SnapshotError("The snapshot revealed answers are invalid.")

    if page == "welcome":
        if round_index != 0 or round_submitted or complete:
            raise SnapshotError("The welcome snapshot status is inconsistent.")
        completed_rounds: list[int] = []
        allowed_choice_rounds: set[int] = set()
    elif page == "round":
        if complete:
            raise SnapshotError("The round snapshot cannot be complete.")
        completed_rounds = list(range(round_index + int(round_submitted)))
        allowed_choice_rounds = set(range(round_index + 1))
    else:
        if round_index != len(ROUNDS) - 1 or not round_submitted or not complete:
            raise SnapshotError("The completion snapshot status is inconsistent.")
        completed_rounds = list(range(len(ROUNDS)))
        allowed_choice_rounds = set(range(len(ROUNDS)))

    expected_result_ids = {
        question_id
        for completed_round in completed_rounds
        for question_id in ROUND_QUESTION_IDS[completed_round]
    }
    if set(results) != expected_result_ids:
        raise SnapshotError("The submitted results do not match the saved page.")

    allowed_choice_ids = {
        question_id
        for allowed_round in allowed_choice_rounds
        for question_id in ROUND_QUESTION_IDS[allowed_round]
    }
    if not set(choices).issubset(allowed_choice_ids):
        raise SnapshotError("The saved choices include a future round.")
    if any(choices.get(question_id) != option_index for question_id, option_index in results.items()):
        raise SnapshotError("The saved choices and results do not agree.")

    completed_slugs = {ROUNDS[index]["slug"] for index in completed_rounds}
    if not set(revealed).issubset(completed_slugs):
        raise SnapshotError("A saved revealed answer belongs to an incomplete round.")

    return {
        "version": SNAPSHOT_VERSION,
        "page": page,
        "round_index": round_index,
        "round_submitted": round_submitted,
        "choices": choices,
        "results": results,
        "complete": complete,
        "order_seed": order_seed,
        "revealed": list(revealed),
    }


def _pairs_to_choice_map(value: object, label: str) -> dict[str, int]:
    if not isinstance(value, list) or len(value) > len(QUESTION_RECORDS):
        raise SnapshotError(f"The compact {label} are invalid.")

    mapped: dict[str, int] = {}
    for pair in value:
        if not isinstance(pair, list) or len(pair) != 2:
            raise SnapshotError(f"The compact {label} are invalid.")
        question_index, option_index = pair
        if not _is_int(question_index) or not 0 <= question_index < len(QUESTION_RECORDS):
            raise SnapshotError(f"The compact {label} reference an unknown question.")
        question_id = QUESTION_RECORDS[question_index][1]["id"]
        if question_id in mapped:
            raise SnapshotError(f"The compact {label} contain a duplicate question.")
        mapped[question_id] = option_index
    return mapped


def _choice_map_to_pairs(choices: Mapping[str, int]) -> list[list[int]]:
    return [
        [QUESTION_INDEX_BY_ID[question_id], option_index]
        for question_id, option_index in sorted(
            choices.items(), key=lambda item: QUESTION_INDEX_BY_ID[item[0]]
        )
    ]


def encode_snapshot(snapshot: object) -> str:
    """Encode a validated snapshot as compact URL-safe compressed JSON."""
    validated = validate_snapshot(snapshot)
    raw: dict[str, Any] = {
        "v": SNAPSHOT_VERSION,
        "p": PAGE_TO_CODE[validated["page"]],
        "i": validated["round_index"],
        "s": validated["round_submitted"],
        "c": _choice_map_to_pairs(validated["choices"]),
        "r": _choice_map_to_pairs(validated["results"]),
        "d": validated["complete"],
        "o": validated["order_seed"],
    }
    if validated["revealed"]:
        raw["x"] = [ROUND_INDEX_BY_SLUG[slug] for slug in validated["revealed"]]

    serialized = json.dumps(raw, separators=(",", ":"), sort_keys=True).encode("utf-8")
    compressed = zlib.compress(serialized, level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")


def decode_snapshot(token: object) -> dict[str, Any]:
    """Decode, validate, and normalize a compact query-parameter snapshot."""
    if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
        raise SnapshotError("The progress token is invalid.")
    try:
        token.encode("ascii")
        padding = "=" * (-len(token) % 4)
        compressed = base64.b64decode(
            token + padding, altchars=b"-_", validate=True
        )
        decompressor = zlib.decompressobj()
        serialized = decompressor.decompress(compressed, MAX_JSON_BYTES + 1)
        if (
            len(serialized) > MAX_JSON_BYTES
            or decompressor.unconsumed_tail
            or not decompressor.eof
            or decompressor.unused_data
        ):
            raise SnapshotError("The progress token is too large or incomplete.")
        raw = json.loads(serialized.decode("utf-8"))
    except (UnicodeError, binascii.Error, zlib.error, json.JSONDecodeError) as error:
        raise SnapshotError("The progress token cannot be decoded.") from error

    required = {"v", "p", "i", "s", "c", "r", "d", "o"}
    allowed = required | {"x"}
    if not isinstance(raw, dict) or not required.issubset(raw) or not set(raw).issubset(allowed):
        raise SnapshotError("The compact snapshot structure is invalid.")
    if raw["v"] != SNAPSHOT_VERSION or raw["p"] not in CODE_TO_PAGE:
        raise SnapshotError("The compact snapshot version or page is invalid.")

    revealed_indexes = raw.get("x", [])
    if not isinstance(revealed_indexes, list) or any(
        not _is_int(index) or not 0 <= index < len(ROUNDS)
        for index in revealed_indexes
    ):
        raise SnapshotError("The compact revealed answers are invalid.")

    expanded = {
        "version": raw["v"],
        "page": CODE_TO_PAGE[raw["p"]],
        "round_index": raw["i"],
        "round_submitted": raw["s"],
        "choices": _pairs_to_choice_map(raw["c"], "choices"),
        "results": _pairs_to_choice_map(raw["r"], "results"),
        "complete": raw["d"],
        "order_seed": raw["o"],
        "revealed": [ROUNDS[index]["slug"] for index in revealed_indexes],
    }
    return validate_snapshot(expanded)


def hydrate_snapshot(snapshot: object) -> dict[str, Any]:
    """Rebuild session data and evaluated results from a validated snapshot."""
    validated = validate_snapshot(snapshot)
    responses: list[dict[str, Any]] = []
    metrics = dict(STARTING_METRICS)
    round_baselines: dict[str, dict[str, int]] = {}

    for round_data in ROUNDS:
        round_results = []
        for question in round_data["questions"]:
            if question["id"] not in validated["results"]:
                continue
            result = evaluate_question(
                question, validated["results"][question["id"]]
            )
            result["round_slug"] = round_data["slug"]
            result["round_title"] = round_data["title"]
            round_results.append(result)
        if round_results:
            round_baselines[round_data["slug"]] = dict(metrics)
            metrics = apply_results(metrics, round_results)
            responses.extend(round_results)

    widget_answers = {
        f"answer-{question_id}": QUESTION_BY_ID[question_id]["options"][option_index]["text"]
        for question_id, option_index in validated["choices"].items()
    }
    return {
        "screen": validated["page"],
        "round_index": validated["round_index"],
        "round_submitted": validated["round_submitted"],
        "responses": responses,
        "metrics": metrics,
        "option_order": create_option_order(validated["order_seed"]),
        "round_baselines": round_baselines,
        "revealed_answers": {slug: True for slug in validated["revealed"]},
        "order_seed": validated["order_seed"],
        "saved_choices": dict(validated["choices"]),
        "widget_answers": widget_answers,
    }
