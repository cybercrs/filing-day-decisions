import unittest
from browser_support import browser_app
from app.content import ROUNDS


def button(app,label):
    return next(item for item in app.button if item.label==label)


class CompleteBrowserLessonTests(unittest.TestCase):
    def test_six_rounds_and_no_new_reveals_on_review(self):
        app=browser_app().run()
        button(app,'Begin the filing review').click().run()
        for index,round_data in enumerate(ROUNDS):
            for i,q in enumerate(round_data['questions']):
                choice=next(o for o in q['options'] if o['correct'] != (index==0 and i==0))
                app.radio(key='answer-'+q['id']).set_value(choice['text']).run()
            button(app,'Submit this round').click().run()
            self.assertTrue(app.session_state.round_submitted)
            self.assertTrue(button(app,'Forward').disabled)
            button(app,'Open the final review' if index==len(ROUNDS)-1 else 'Continue to the next round').click().run()
            before=app.query_params['progress']
            button(app,'Back').click().run()
            self.assertFalse(app.exception)
            self.assertEqual([b.label for b in app.main.button],['Back','Forward'])
            self.assertEqual(app.query_params['progress'],before)
            self.assertFalse(any(app.session_state.revealed_answers.values()))
            button(app,'Forward').click().run()
        self.assertEqual(app.session_state.screen,'debrief')
        self.assertEqual(len(app.session_state.responses),19)
        self.assertEqual(sum(r['is_correct'] for r in app.session_state.responses),18)
