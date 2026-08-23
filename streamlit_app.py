"""Interactive financial reporting simulation."""

from __future__ import annotations

import html
import random

import streamlit as st

from app.content import ROUNDS
from app.engine import (
    METRIC_LABELS,
    STARTING_METRICS,
    apply_results,
    evaluate_question,
    summarize_results,
)


st.set_page_config(
    page_title="Filing Day Decisions",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CUSTOM_CSS = """
<style>
    :root {
        --ud-blue: #003087;
        --ud-red: #CE0037;
        --ink: #17233A;
        --muted: #5B677A;
        --paper: #FFFFFF;
        --mist: #E9EFF8;
        --line: #D5DEEB;
        --success: #177245;
        --warning: #9A5A00;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 92% 0%, rgba(206, 0, 55, 0.08), transparent 30rem),
            linear-gradient(180deg, #F8FAFD 0%, #F3F6FB 100%);
    }

    [data-testid="stHeader"] {
        background: rgba(248, 250, 253, 0.88);
        border-bottom: 1px solid rgba(213, 222, 235, 0.8);
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1120px;
        padding-top: 3.2rem;
        padding-bottom: 5rem;
    }

    h1, h2, h3 {
        color: var(--ud-blue);
        letter-spacing: -0.025em;
    }

    h1 {
        font-size: clamp(2.2rem, 5vw, 4rem) !important;
        line-height: 1.02 !important;
    }

    p, li, label {
        color: var(--ink);
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: clamp(2rem, 5vw, 4.5rem);
        border-radius: 28px;
        color: white;
        background: linear-gradient(135deg, #003087 0%, #001E55 100%);
        box-shadow: 0 24px 70px rgba(0, 48, 135, 0.22);
    }

    .hero::after {
        content: "";
        position: absolute;
        width: 22rem;
        height: 22rem;
        right: -7rem;
        bottom: -11rem;
        border: 3.5rem solid rgba(206, 0, 55, 0.92);
        border-radius: 50%;
    }

    .hero > * {
        position: relative;
        z-index: 1;
    }

    .hero-kicker, .eyebrow {
        margin: 0 0 0.8rem;
        color: #D9E8FF;
        font-size: 0.79rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }

    .hero h1 {
        max-width: 760px;
        margin: 0;
        color: white;
    }

    .hero-copy {
        max-width: 690px;
        margin: 1.4rem 0 0;
        color: #ECF3FF;
        font-size: 1.12rem;
        line-height: 1.65;
    }

    .hero-rule {
        width: 84px;
        height: 7px;
        margin: 1.4rem 0;
        border-radius: 99px;
        background: var(--ud-red);
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
        margin: 1.5rem 0 1.9rem;
    }

    .feature-card, .scenario-card, .question-card, .feedback-card,
    .metric-card, .debrief-card, .round-nav, .reflection-card {
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.94);
        box-shadow: 0 10px 32px rgba(16, 38, 75, 0.07);
    }

    .feature-card {
        min-height: 142px;
        padding: 1.25rem;
        border-radius: 18px;
    }

    .feature-card strong {
        display: block;
        margin-bottom: 0.4rem;
        color: var(--ud-blue);
        font-size: 1.04rem;
    }

    .feature-card span {
        color: var(--muted);
        line-height: 1.5;
    }

    .round-nav {
        padding: 0.85rem 1rem;
        border-radius: 16px;
    }

    .round-dots {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.45rem;
    }

    .round-dot {
        height: 8px;
        border-radius: 99px;
        background: #DCE4F0;
    }

    .round-dot.done { background: var(--ud-blue); }
    .round-dot.current { background: var(--ud-red); }

    .scenario-card {
        padding: 1.5rem 1.6rem;
        margin: 1.1rem 0 1.35rem;
        border-left: 7px solid var(--ud-red);
        border-radius: 18px;
    }

    .scenario-card p { margin: 0; line-height: 1.65; }
    .scenario-card .goal { margin-top: 0.7rem; color: var(--muted); }

    .question-card {
        padding: 1.15rem 1.25rem 0.3rem;
        margin: 0.9rem 0 0.25rem;
        border-radius: 16px;
    }

    .question-number {
        margin: 0 0 0.35rem;
        color: var(--ud-red);
        font-size: 0.77rem;
        font-weight: 800;
        letter-spacing: 0.11em;
        text-transform: uppercase;
    }

    .question-prompt {
        margin: 0;
        color: var(--ink);
        font-size: 1.04rem;
        font-weight: 720;
        line-height: 1.5;
    }

    .disclosure-panel {
        margin: 0.9rem 0 1rem;
        padding: 1rem;
        border: 1px solid var(--line);
        border-radius: 13px;
        background: #F8FAFD;
    }

    .disclosure-label {
        display: block;
        margin-bottom: 0.42rem;
        color: var(--ud-blue);
        font-size: 0.72rem;
        font-weight: 850;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .disclosure-text {
        margin: 0;
        color: var(--ink);
        font-weight: 520;
        line-height: 1.65;
    }

    .fact-block {
        margin: 0.85rem 0 0;
        padding-top: 0.85rem;
        border-top: 1px solid var(--line);
    }

    div[data-testid="stRadio"] {
        padding: 0.25rem 0.15rem 1rem;
    }

    div[role="radiogroup"] label {
        padding: 0.7rem 0.8rem;
        border: 1px solid transparent;
        border-radius: 12px;
    }

    div[role="radiogroup"] label:hover {
        border-color: #B8C8DF;
        background: #F6F9FD;
    }

    .feedback-card {
        padding: 1.25rem 1.35rem;
        margin: 0.85rem 0;
        border-radius: 17px;
    }

    .feedback-card.correct { border-left: 7px solid var(--success); }
    .feedback-card.review { border-left: 7px solid var(--warning); }
    .feedback-label { margin: 0 0 0.35rem; font-weight: 800; }
    .feedback-label.correct { color: var(--success); }
    .feedback-label.review { color: var(--warning); }
    .feedback-card p { margin: 0.35rem 0; line-height: 1.55; }
    .concept-pill {
        display: inline-block;
        margin-top: 0.55rem;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        color: var(--ud-blue);
        background: var(--mist);
        font-size: 0.76rem;
        font-weight: 750;
    }

    .metric-card {
        height: 100%;
        padding: 1rem;
        border-radius: 15px;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.6rem;
        margin-bottom: 1.35rem;
    }

    .metric-label {
        min-height: 2.4em;
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 750;
        line-height: 1.25;
        text-transform: uppercase;
    }

    .metric-value {
        margin: 0.25rem 0 0.45rem;
        color: var(--ud-blue);
        font-size: 1.55rem;
        font-weight: 850;
    }

    .metric-delta {
        margin-left: 0.28rem;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .metric-delta.positive { color: #177245; }
    .metric-delta.negative { color: #A62232; }
    .metric-delta.neutral { color: var(--muted); }

    .metric-track {
        display: flex;
        height: 7px;
        overflow: hidden;
        border-radius: 99px;
        background: #E1E7F0;
    }

    .metric-fill {
        height: 100%;
        border-radius: 99px;
        background: linear-gradient(90deg, var(--ud-blue), #2768B5);
    }

    .metric-segment { height: 100%; }
    .metric-segment.carried { background: var(--ud-blue); }
    .metric-segment.lost { background: #CE0037; }
    .metric-segment.gained { background: #24915E; }

    .metric-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem 1.1rem;
        margin: -0.55rem 0 1.4rem;
        color: var(--muted);
        font-size: 0.77rem;
        font-weight: 700;
    }

    .legend-item { display: inline-flex; align-items: center; gap: 0.35rem; }
    .legend-swatch { width: 12px; height: 7px; border-radius: 99px; }
    .legend-swatch.carried { background: var(--ud-blue); }
    .legend-swatch.lost { background: #CE0037; }
    .legend-swatch.gained { background: #24915E; }

    .reflection-card {
        padding: 1.25rem 1.35rem;
        margin: 1.3rem 0 0.8rem;
        border-left: 7px solid var(--ud-blue);
        border-radius: 17px;
    }

    .reflection-card .eyebrow {
        margin-bottom: 0.45rem;
        color: var(--ud-blue);
    }

    .reflection-question {
        margin: 0;
        color: var(--ink);
        font-size: 1.04rem;
        font-weight: 760;
        line-height: 1.55;
    }

    .revealed-answer {
        padding: 1rem 1.1rem;
        margin: 0.75rem 0 1.2rem;
        border-left: 6px solid #24915E;
        border-radius: 13px;
        background: #ECF8F1;
        color: #164E35;
        line-height: 1.6;
    }

    .begin-spacer { height: 1rem; }

    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    .debrief-hero {
        padding: clamp(1.8rem, 5vw, 3.8rem);
        border-radius: 26px;
        color: white;
        background: linear-gradient(135deg, #003087 0%, #001E55 75%);
        box-shadow: 0 24px 70px rgba(0, 48, 135, 0.2);
    }

    .debrief-hero h1, .debrief-hero p { color: white; }
    .debrief-score { color: #FFCCD9 !important; font-size: 1.1rem; font-weight: 800; }
    .debrief-card {
        min-height: 190px;
        padding: 1.35rem;
        border-radius: 18px;
    }
    .debrief-card h3 { margin-top: 0; }
    .debrief-card li { margin-bottom: 0.45rem; }

    .stButton > button, .stFormSubmitButton > button {
        min-height: 3.05rem;
        border: 0;
        border-radius: 12px;
        color: white;
        background: #334155;
        font-weight: 800;
        box-shadow: 0 8px 18px rgba(51, 65, 85, 0.18);
    }

    .stButton > button p, .stFormSubmitButton > button p {
        color: #FFFFFF !important;
    }

    .stButton > button:hover, .stFormSubmitButton > button:hover {
        color: white;
        background: #1F2937;
        transform: translateY(-1px);
    }

    .stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {
        outline: 3px solid #78A9E6;
        outline-offset: 3px;
    }

    [data-testid="stAlert"] { border-radius: 13px; }

    footer { visibility: hidden; }

    @media (max-width: 760px) {
        [data-testid="stMainBlockContainer"] { padding-top: 1.7rem; }
        .feature-grid { grid-template-columns: 1fr; }
        .feature-card { min-height: auto; }
        .hero::after { opacity: 0.55; }
        .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .metric-label { min-height: 0; }
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def safe(text: object) -> str:
    return html.escape(str(text), quote=True)


def scroll_to_top(transition_token: str) -> None:
    """Place each new activity screen at its introduction after a rerun."""
    st.html(
        f"""
        <script>
            (() => {{
                document.documentElement.dataset.filingTransition = "{safe(transition_token)}";
                const goToTop = () => {{
                    const doc = document;
                    const targets = [
                        doc.querySelector('[data-testid="stMain"]'),
                        doc.querySelector('[data-testid="stAppViewContainer"]'),
                        doc.scrollingElement,
                        doc.documentElement,
                        doc.body
                    ].filter(Boolean);
                    targets.forEach((target) => target.scrollTo({{ top: 0, left: 0, behavior: 'auto' }}));
                    window.scrollTo({{ top: 0, left: 0, behavior: 'auto' }});
                }};
                requestAnimationFrame(() => requestAnimationFrame(goToTop));
                window.setTimeout(goToTop, 120);
            }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def initialize_state() -> None:
    defaults = {
        "screen": "welcome",
        "round_index": 0,
        "round_submitted": False,
        "responses": [],
        "metrics": dict(STARTING_METRICS),
        "option_order": {},
        "round_baselines": {},
        "revealed_answers": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not st.session_state.option_order:
        st.session_state.option_order = create_option_order()


def create_option_order() -> dict[str, list[int]]:
    """Randomize answer placement without changing the underlying scoring data."""
    return {
        question["id"]: random.sample(
            range(len(question["options"])), k=len(question["options"])
        )
        for round_data in ROUNDS
        for question in round_data["questions"]
    }


def reset_activity() -> None:
    st.session_state.screen = "round"
    st.session_state.round_index = 0
    st.session_state.round_submitted = False
    st.session_state.responses = []
    st.session_state.metrics = dict(STARTING_METRICS)
    st.session_state.option_order = create_option_order()
    st.session_state.round_baselines = {}
    st.session_state.revealed_answers = {}
    for key in list(st.session_state):
        if key.startswith("answer-"):
            del st.session_state[key]


def render_welcome() -> None:
    scroll_to_top("welcome")
    st.markdown(
        """
        <section class="hero">
            <p class="hero-kicker">A financial reporting simulation</p>
            <h1>Filing Day<br>Decisions</h1>
            <div class="hero-rule"></div>
            <p class="hero-copy">
                Gem City Goods is almost ready to release its annual financial report.
                You are the final reviewer. Make the choices that help users receive
                relevant, faithful, comparable, timely, and understandable information.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="feature-grid">
            <div class="feature-card">
                <strong>6 connected rounds</strong>
                <span>Move from the reporting rulebook through measurement and disclosure.</span>
            </div>
            <div class="feature-card">
                <strong>19 filing decisions</strong>
                <span>Choose an action, then see why it improves—or weakens—the report.</span>
            </div>
            <div class="feature-card">
                <strong>One final review</strong>
                <span>Review strengths, concepts to revisit, and the complete decision trail.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Your assignment")
    st.write(
        "Work through the filing in order. Each round introduces a short business "
        "situation using straightforward transactions and reporting decisions."
    )
    st.markdown(
        "- Choose the best response before seeing feedback.\n"
        "- Watch the five reporting gauges change with your decisions.\n"
        "- Use the final screen to review your complete decision trail."
    )

    st.markdown('<div class="begin-spacer"></div>', unsafe_allow_html=True)
    if st.button("Begin the filing review", type="primary", use_container_width=True):
        reset_activity()
        st.rerun()


def render_round_progress(current_index: int) -> None:
    dots = []
    for index in range(len(ROUNDS)):
        state = "done" if index < current_index else "current" if index == current_index else ""
        dots.append(f'<span class="round-dot {state}"></span>')
    st.markdown(
        '<div class="round-nav"><div class="round-dots">'
        + "".join(dots)
        + "</div></div>",
        unsafe_allow_html=True,
    )


def render_metrics(
    metrics: dict[str, int],
    heading: str = "Your reporting gauges",
    baseline: dict[str, int] | None = None,
) -> None:
    st.markdown(f"### {safe(heading)}")
    cards = []
    for metric, label in METRIC_LABELS.items():
        value = metrics[metric]
        if baseline is None:
            delta_html = ""
            track_html = (
                f'<div class="metric-segment carried" style="width:{value}%"></div>'
            )
        else:
            delta = value - baseline[metric]
            delta_class = "positive" if delta > 0 else "negative" if delta < 0 else "neutral"
            delta_html = f'<span class="metric-delta {delta_class}">{delta:+d}</span>'
            if delta > 0:
                track_html = (
                    f'<div class="metric-segment carried" style="width:{baseline[metric]}%"></div>'
                    f'<div class="metric-segment gained" style="width:{delta}%"></div>'
                )
            elif delta < 0:
                track_html = (
                    f'<div class="metric-segment carried" style="width:{value}%"></div>'
                    f'<div class="metric-segment lost" style="width:{abs(delta)}%"></div>'
                )
            else:
                track_html = (
                    f'<div class="metric-segment carried" style="width:{value}%"></div>'
                )
        cards.append(
            f'<div class="metric-card">'
            f'<div class="metric-label">{safe(label)}</div>'
            f'<div class="metric-value">{value}{delta_html}</div>'
            f'<div class="metric-track">{track_html}</div>'
            f'</div>'
        )
    st.markdown(
        '<div class="metric-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )
    if baseline is not None:
        st.markdown(
            '<div class="metric-legend">'
            '<span class="legend-item"><span class="legend-swatch carried"></span>Points already there</span>'
            '<span class="legend-item"><span class="legend-swatch lost"></span>Net points lost</span>'
            '<span class="legend-item"><span class="legend-swatch gained"></span>Net points gained</span>'
            '</div>',
            unsafe_allow_html=True,
        )


def submit_round(round_data: dict[str, object], selections: list[str | None]) -> None:
    questions = round_data["questions"]
    if any(selection is None for selection in selections):
        st.warning("Make a decision for every item before submitting this round.")
        return

    results = []
    for question, selection in zip(questions, selections):
        option_texts = [option_data["text"] for option_data in question["options"]]
        selected_index = option_texts.index(selection)
        result = evaluate_question(question, selected_index)
        result["round_slug"] = round_data["slug"]
        result["round_title"] = round_data["title"]
        results.append(result)

    baseline = dict(st.session_state.metrics)
    updated_metrics = apply_results(baseline, results)
    st.session_state.responses.extend(results)
    st.session_state.round_baselines[round_data["slug"]] = baseline
    st.session_state.metrics = updated_metrics
    st.session_state.round_submitted = True
    st.rerun()


def render_feedback(round_data: dict[str, object]) -> None:
    round_results = [
        result
        for result in st.session_state.responses
        if result["round_slug"] == round_data["slug"]
    ]
    correct_count = sum(result["is_correct"] for result in round_results)
    st.success(
        f"Round complete: {correct_count} of {len(round_results)} decisions matched the strongest reporting choice."
    )

    for result in round_results:
        status_class = "correct" if result["is_correct"] else "review"
        status_text = "Strong decision" if result["is_correct"] else "Review this decision"
        answer_note = (
            ""
            if result["is_correct"]
            else f'<p><strong>Stronger choice:</strong> {safe(result["correct_text"])}</p>'
        )
        feedback_html = (
            f'<div class="feedback-card {status_class}">'
            f'<p class="feedback-label {status_class}">{status_text}</p>'
            f'<p><strong>{safe(result["prompt"])}</strong></p>'
            f'<p>{safe(result["feedback"])}</p>'
            f'{answer_note}'
            f'<p>{safe(result["explanation"])}</p>'
            f'<span class="concept-pill">{safe(result["concept"])}</span>'
            f'</div>'
        )
        st.markdown(
            feedback_html,
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="reflection-card">'
        f'<p class="eyebrow">Test your thinking</p>'
        f'<p class="reflection-question">{safe(round_data["reflection_question"])}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    slug = round_data["slug"]
    if not st.session_state.revealed_answers.get(slug, False):
        if st.button("Reveal answer", key=f"reveal-{slug}", use_container_width=True):
            st.session_state.revealed_answers[slug] = True
    if st.session_state.revealed_answers.get(slug, False):
        st.markdown(
            f'<div class="revealed-answer">{safe(round_data["reflection_answer"])}</div>',
            unsafe_allow_html=True,
        )

    render_metrics(
        st.session_state.metrics,
        "Gauges after this round",
        baseline=st.session_state.round_baselines[slug],
    )

    is_last = st.session_state.round_index == len(ROUNDS) - 1
    label = "Open the final review" if is_last else "Continue to the next round"
    if st.button(label, type="primary", use_container_width=True):
        if is_last:
            st.session_state.screen = "debrief"
        else:
            st.session_state.round_index += 1
            st.session_state.round_submitted = False
        st.rerun()


def render_round() -> None:
    round_index = st.session_state.round_index
    round_state = "feedback" if st.session_state.round_submitted else "decisions"
    scroll_to_top(f"round-{round_index}-{round_state}")
    round_data = ROUNDS[round_index]
    render_round_progress(round_index)
    st.markdown(f'<p class="eyebrow" style="color:#CE0037;margin-top:1.5rem;">{safe(round_data["eyebrow"])}</p>', unsafe_allow_html=True)
    st.title(round_data["title"])
    st.markdown(
        f"""
        <div class="scenario-card">
            <p>{safe(round_data['scenario'])}</p>
            <p class="goal"><strong>Learning goal:</strong> {safe(round_data['goal'])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.round_submitted:
        render_feedback(round_data)
        return

    render_metrics(st.session_state.metrics)
    st.markdown("### Decision file")

    selections: list[str | None] = []
    with st.form(f"round-form-{round_data['slug']}", clear_on_submit=False):
        for index, question in enumerate(round_data["questions"], start=1):
            disclosure_html = ""
            if "draft_paragraph" in question:
                disclosure_html = (
                    '<div class="disclosure-panel">'
                    '<span class="disclosure-label">Draft disclosure</span>'
                    f'<p class="disclosure-text">{safe(question["draft_paragraph"])}</p>'
                    '<div class="fact-block">'
                    '<span class="disclosure-label">Fact</span>'
                    f'<p class="disclosure-text">{safe(question["fact"])}</p>'
                    '</div>'
                    '</div>'
                )
            question_html = (
                '<div class="question-card">'
                f'<p class="question-number">Decision {index}</p>'
                f'{disclosure_html}'
                f'<p class="question-prompt">{safe(question["prompt"])}</p>'
                '</div>'
            )
            st.markdown(
                question_html,
                unsafe_allow_html=True,
            )
            selection = st.radio(
                f"Decision {index}",
                options=[
                    question["options"][option_index]["text"]
                    for option_index in st.session_state.option_order[question["id"]]
                ],
                index=None,
                key=f"answer-{question['id']}",
                label_visibility="collapsed",
            )
            selections.append(selection)

        submitted = st.form_submit_button(
            "Submit this round", type="primary", use_container_width=True
        )

    if submitted:
        submit_round(round_data, selections)


def render_debrief() -> None:
    scroll_to_top("debrief")
    summary = summarize_results(st.session_state.responses)
    st.markdown(
        f"""
        <section class="debrief-hero">
            <p class="hero-kicker">Filing review complete</p>
            <h1>{safe(summary['status'])}</h1>
            <p class="debrief-score">{summary['correct']} of {summary['total']} strongest decisions · {summary['percent']}%</p>
            <p>{safe(summary['message'])}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    render_metrics(
        st.session_state.metrics,
        "Final reporting profile",
        baseline=STARTING_METRICS,
    )

    left, right = st.columns(2, gap="large")
    with left:
        strengths = summary["strengths"] or ["Keep building across every concept area"]
        items = "".join(f"<li>{safe(concept)}</li>" for concept in strengths)
        st.markdown(
            f'<div class="debrief-card"><h3>Concept strengths</h3><ul>{items}</ul></div>',
            unsafe_allow_html=True,
        )
    with right:
        review = summary["review"] or ["No concept area requires immediate review"]
        items = "".join(f"<li>{safe(concept)}</li>" for concept in review)
        st.markdown(
            f'<div class="debrief-card"><h3>Concepts to revisit</h3><ul>{items}</ul></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Your decision trail")
    for round_data in ROUNDS:
        round_results = [
            result
            for result in st.session_state.responses
            if result["round_slug"] == round_data["slug"]
        ]
        correct = sum(result["is_correct"] for result in round_results)
        with st.expander(
            f"{round_data['title']} · {correct}/{len(round_results)} strongest decisions"
        ):
            for result in round_results:
                marker = "✓" if result["is_correct"] else "↻"
                st.markdown(f"**{marker} {result['prompt']}**")
                st.write(f"Your decision: {result['selected_text']}")
                if not result["is_correct"]:
                    st.write(f"Stronger choice: {result['correct_text']}")
                st.caption(f"{result['concept']} · {result['explanation']}")

    if st.button("Start a new filing review", use_container_width=True):
        reset_activity()
        st.rerun()


initialize_state()

if st.session_state.screen == "welcome":
    render_welcome()
elif st.session_state.screen == "round":
    render_round()
else:
    render_debrief()
