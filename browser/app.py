"""Filing review uses its original scoring and reveal rules."""
import runpy
from pathlib import Path
import sys
# Stlite puts the entrypoint directory first; keep root packages authoritative.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from browser.common import LiveUI, ReviewUI, VIEW_KEY, restore_view, keep_widgets, navigation, save_view, scroll
from browser.navigation import frontier

app = runpy.run_path(str(Path(__file__).with_name('shared_app.py')))
g = app['advance_round'].__globals__
app['initialize_state']()
if VIEW_KEY not in st.session_state:
    restore_view(st.session_state, st.query_params.get('view'), frontier(st.session_state))
    st.session_state['_browser_widgets'] = sorted(key for key in st.session_state if key.startswith('answer-'))
keep_widgets(st.session_state)


def restart():
    if st.session_state[VIEW_KEY] == frontier(st.session_state):
        app['reset_activity']()
        st.session_state[VIEW_KEY] = frontier(st.session_state)
        st.session_state['_browser_scroll'] = True


def advance():
    if st.session_state[VIEW_KEY] == frontier(st.session_state) and st.session_state.round_submitted:
        app['advance_round']()
        st.session_state[VIEW_KEY] = frontier(st.session_state)
        st.session_state['_browser_scroll'] = True


g.update(st=LiveUI(), reset_activity=restart, advance_round=advance)
reached = frontier(st.session_state)
navigation(st.session_state, reached, len(app['ROUNDS']) + 2)
view = st.session_state[VIEW_KEY]
if view < reached:
    ui = ReviewUI(st.session_state)
    if view == 0:
        ui.session_state.screen = 'welcome'
    else:
        ui.session_state.screen = 'round'
        ui.session_state.round_index = view - 1
        ui.session_state.round_submitted = True
        round_data = app['ROUNDS'][view - 1]
        baseline = ui.session_state.round_baselines[round_data['slug']]
        results = [r for r in ui.session_state.responses if r['round_slug'] == round_data['slug']]
        ui.session_state.metrics = app['apply_results'](baseline, results)
    g['st'] = ui
if view == 0:
    app['render_welcome']()
elif view == len(app['ROUNDS']) + 1:
    app['render_debrief']()
else:
    app['render_round']()
g['st'] = st
app['persist_progress']()
save_view(st.session_state)
scroll()
