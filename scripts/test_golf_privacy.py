import json
from pathlib import Path
import tempfile
import unittest
import golf_privacy


class GolfPrivacy(unittest.TestCase):
    def test_reimported_names_are_removed_from_data_without_changing_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'data'
            data.mkdir()
            name = 'Example Members Club'
            policy = {'excluded_course_fingerprints': [golf_privacy.fingerprint(name)]}
            (data / 'golf-privacy.json').write_text(json.dumps(policy))
            rounds = {'recent_rounds': [{'course': name, 'score': 80, 'differential': 7.4}],
                      'course_history': [{'course': name, 'rounds': 1}], 'index': 4.1}
            courses = {'courses': [{'name': name}, {'name': 'Public Example'}]}
            for filename, value in [('golf.json', rounds), ('courses.json', courses)]:
                (data / filename).write_text(json.dumps(value))
            for _ in range(2):
                # Simulate a later raw import, then the normal website build.
                (data / 'golf.json').write_text(json.dumps(rounds))
                golf_privacy.apply(root)
                result = json.loads((data / 'golf.json').read_text())
                self.assertEqual(result['recent_rounds'][0],
                                 {'course': 'Private course', 'score': 80, 'differential': 7.4})
                self.assertEqual(result['course_history'][0]['course'], 'Private course')
                self.assertEqual(result['index'], 4.1)
                self.assertEqual(json.loads((data / 'courses.json').read_text()),
                                 {'courses': [{'name': 'Public Example'}]})
                self.assertEqual(golf_privacy.apply(root), [])

    def test_case_spacing_and_punctuation_do_not_bypass_matching(self):
        self.assertEqual(golf_privacy.fingerprint('Example Club - North'),
                         golf_privacy.fingerprint('EXAMPLE club: north'))

    def test_invalid_privacy_policy_stops_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'data/golf-privacy.json').write_text('{broken')
            with self.assertRaises(json.JSONDecodeError):
                golf_privacy.apply(root)

if __name__ == '__main__':
    unittest.main()
