"""Export the unchanged filing case and renderer variants for native delivery."""
from __future__ import annotations
import copy
import itertools
import json
import random
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from browser.build import shared_source
from app import content as case, engine, progress

class State(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key, value):
        self[key] = value


class Container:
    def __init__(self, recorder, node):
        self.recorder, self.node = recorder, node

    def __enter__(self):
        self.recorder.stack.append(self.node["children"])
        return self

    def __exit__(self, *args):
        self.recorder.stack.pop()

    def metric(self, label, value, **kwargs):
        self.node["children"].append({"kind": "metric", "label": label, "value": value})


class Recorder:
    def __init__(self):
        self.session_state = State()
        self.stack = [[]]

    def node(self, kind, **kwargs):
        node = {"kind": kind, **kwargs}
        self.stack[-1].append(node)
        return node

    def set_page_config(self, **kwargs):
        pass

    def markdown(self, text, unsafe_allow_html=False):
        self.node("html" if unsafe_allow_html else "markdown", text=text.strip())

    def __getattr__(self, kind):
        if kind in {"title", "header", "subheader", "write", "success", "warning", "info", "caption", "error"}:
            return lambda text: self.node(kind, text=text.replace(r"\$", "$"))
        raise AttributeError(kind)

    def radio(self, label, options, **kwargs):
        options = list(options)
        self.node("radio", label=label.replace(r"\$", "$"),
                  options=[x.replace(r"\$", "$") for x in options], key=kwargs["key"])
        index = kwargs.get("index", 0)
        value = self.session_state.get(kwargs["key"], options[index] if index is not None else None)
        self.session_state[kwargs["key"]] = value
        return value

    def selectbox(self, label, options, **kwargs):
        options = list(options)
        self.node("select", label=label, options=options, key=kwargs["key"])
        index = kwargs.get("index", 0)
        value = self.session_state.get(kwargs["key"], options[index] if index is not None else None)
        self.session_state[kwargs["key"]] = value
        return value

    def button(self, label, **kwargs):
        self.node("button", label=label, key=kwargs.get("key"),
                  disabled=kwargs.get("disabled", False),
                  action=kwargs.get("on_click").__name__ if kwargs.get("on_click") else None)
        return False

    def form_submit_button(self, label, **kwargs):
        self.node("button", label=label, action=kwargs["on_click"].__name__)
        return False

    def progress(self, value, **kwargs):
        self.node("progress", value=value)

    def columns(self, count, **kwargs):
        count = count if isinstance(count, int) else len(count)
        group = self.node("columns", children=[])
        columns = []
        for _ in range(count):
            node = {"kind": "column", "children": []}
            group["children"].append(node)
            columns.append(Container(self, node))
        return columns

    def tabs(self, labels):
        group = self.node("tabs", children=[])
        tabs = []
        for label in labels:
            node = {"kind": "tab", "label": label, "children": []}
            group["children"].append(node)
            tabs.append(Container(self, node))
        return tabs

    def form(self, key):
        return Container(self, self.node("form", key=key, children=[]))

    def expander(self, label, **kwargs):
        return Container(self, self.node("details", label=label,
                                        expanded=kwargs.get("expanded", False), children=[]))


    def number_input(self, label, **kwargs):
        self.node("number", label=label, key=kwargs["key"], value=kwargs.get("value"),
                  step=kwargs.get("step", 1), placeholder=kwargs.get("placeholder", ""))
        return self.session_state.get(kwargs["key"], kwargs.get("value"))

    def multiselect(self, label, options, **kwargs):
        self.node("many", label=label, options=list(options), key=kwargs["key"], help=kwargs.get("help"))
        return self.session_state.get(kwargs["key"], [])

    def text_area(self, label, **kwargs):
        self.node("text", label=label, key=kwargs["key"], placeholder=kwargs.get("placeholder"),
                  maxLength=kwargs.get("max_chars"), help=kwargs.get("help"))
        return self.session_state.get(kwargs["key"], "")

    def dataframe(self, rows, **kwargs):
        self.node("table", rows=rows)

    def divider(self):
        self.node("divider")

    @property
    def sidebar(self):
        return Container(self, self.node("sidebar", children=[]))

    @contextmanager
    def capture(self):
        self.stack = [[]]
        yield self.stack[0]


def snapshot_at(position, submitted=False, correct=True, revealed=False, seed=0):
    state = progress.welcome_snapshot(seed)
    if position == 0:
        return state
    state.update(page="debrief" if position == 7 else "round",
                 round_index=5 if position == 7 else position - 1,
                 round_submitted=True if position == 7 else submitted, complete=position == 7)
    for index, round_data in enumerate(case.ROUNDS):
        if index < state["round_index"] or index == state["round_index"] and state["round_submitted"]:
            for question in round_data["questions"]:
                answer = next(i for i, option in enumerate(question["options"]) if bool(option["correct"]) == correct)
                state["choices"][question["id"]] = answer
                state["results"][question["id"]] = answer
            if revealed:
                state["revealed"].append(round_data["slug"])
    return progress.validate_snapshot(state)


def export():
    here = Path(__file__).resolve().parent
    recorder = Recorder()
    namespace = {}
    with patch.dict(sys.modules, {"streamlit": recorder}):
        exec(compile(shared_source(), "original_teaching_renderer", "exec"), namespace)
    namespace["scroll_to_top"] = lambda *args: None
    namespace["render_metrics"] = lambda metrics, heading="Your reporting gauges", baseline=None: recorder.node(
        "gauges", heading=heading, baseline=baseline is not None)
    namespace["render_feedback"] = lambda round_data: recorder.node("round-feedback", slug=round_data["slug"])
    screens = []
    legacy = []
    for position in range(8):
        variants = {}
        for status in ("unanswered", "correct", "wrong", "revealed"):
            snapshot = snapshot_at(position, status != "unanswered",
                                   correct=status != "wrong", revealed=status == "revealed")
            values = progress.hydrate_snapshot(snapshot)
            widgets = values.pop("widget_answers")
            values.update(widgets, validation_warning=False)
            recorder.session_state = State(values)
            with recorder.capture() as nodes:
                namespace["render_welcome" if position == 0 else "render_debrief" if position == 7 else "render_round"]()
            variants[status] = nodes
            if status == "unanswered":
                legacy.append({"token": progress.encode_snapshot(snapshot), "snapshot": snapshot})
        screens.append(variants)
    (here / "content.js").write_text("// Generated from unchanged Python teaching renderers and case data.\nexport const DATA="
        + json.dumps({"title": "Filing Day Decisions", "rounds": case.ROUNDS,
            "metricLabels": engine.METRIC_LABELS, "startingMetrics": engine.STARTING_METRICS,
            "screens": screens}, ensure_ascii=True, separators=(",", ":")) + ";\n")
    (here / "original.css").write_text(namespace["CUSTOM_CSS"].replace("<style>", "").replace("</style>", "").strip() + "\n")
    (here / "tests/legacy-links.json").write_text(json.dumps(legacy, indent=2) + "\n")
    rng = random.Random(31059)
    outcomes = []
    for round_data in case.ROUNDS:
        for question in round_data["questions"]:
            for index in range(len(question["options"])):
                outcomes.append({"id": question["id"], "index": index,
                                 "result": engine.evaluate_question(question, index)})
    trajectories = []
    for attempt in range(80):
        state = snapshot_at(7)
        state["order_seed"] = rng.randrange(2**32)
        for question in progress.QUESTION_BY_ID.values():
            choice = rng.randrange(len(question["options"]))
            state["choices"][question["id"]] = state["results"][question["id"]] = choice
        hydrated = progress.hydrate_snapshot(state)
        trajectories.append({"snapshot": state, "responses": hydrated["responses"],
            "metrics": hydrated["metrics"], "baselines": hydrated["round_baselines"],
            "summary": engine.summarize_results(hydrated["responses"]),
            "trace": engine.apply_results_with_changes(engine.STARTING_METRICS, hydrated["responses"])})
    fixtures = {"outcomes": outcomes, "trajectories": trajectories,
        "orders": [{"seed": seed, "order": progress.create_option_order(seed)}
                   for seed in (0, 1, 42, 2**31, 2**32 - 1)],
        "snapshots": [{"snapshot": snapshot_at(position, submitted=True, correct=False, revealed=True, seed=42),
            "token": progress.encode_snapshot(snapshot_at(position, submitted=True, correct=False, revealed=True, seed=42))}
            for position in range(8)]}
    (here / "tests/python-oracles.json").write_text(json.dumps(fixtures, indent=2) + "\n")
    print(json.dumps({"rounds": len(case.ROUNDS), "decisions": len(progress.QUESTION_RECORDS),
        "option_outcomes": len(outcomes), "random_trajectories": 80,
        "app_owned_assets": [], "curriculum_changes": []}, indent=2))


if __name__ == "__main__":
    export()
