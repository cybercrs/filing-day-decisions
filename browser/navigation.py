"""Welcome, six connected rounds, and final review."""
from app.content import ROUNDS

def frontier(state):
    if state['screen'] == 'welcome':
        return 0
    if state['screen'] == 'debrief':
        return len(ROUNDS) + 1
    return state['round_index'] + 1
