import json
import os
import tempfile
import unittest
from unittest import mock

import sync_goodreads as sg


def js(page):
    """HTML inside a JavaScript string, the way Goodreads sends a widget."""
    text = page.replace('"', '\\"').replace('</', '<\\/').replace('\n', '\\n')
    return f"  var widget_code = '{text}'\n  document.write(widget_code)\n"


def grid(*rows):
    body = ''.join(f'<div class="gr_grid_book_container"><a title="{title}" rel="nofollow" '
                   f'href="https://www.goodreads.com/review/show/{review}?utm_medium=api"></a></div>\n'
                   for title, review in rows)
    return js(f'<div class="gr_grid_container">\n{body}</div>')


def authors(*rows):
    body = ''.join(f'<div class="gr_custom_each_container_1"><a href="/review/show/{review}">x</a>'
                   f'<div class="gr_custom_author_1">\n by <a href="/author/show/1">{name}</a>\n</div></div>'
                   for review, name in rows)
    return js(f'<div class="gr_custom_container_1">{body}</div>')


class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.mkdir(os.path.join(self.tmp.name, 'data'))
        self.books = os.path.join(self.tmp.name, 'data', 'books.json')
        json.dump({'books': [{'title': 'Atomic Habits', 'author': 'James Clear', 'finished': '2024-01-01'}]},
                  open(self.books, 'w'))
        json.dump({'sha256': []}, open(os.path.join(self.tmp.name, 'data', 'hidden.json'), 'w'))
        self.read = grid(('Atomic Habits: An Easy &amp; Proven Way', '1'), ('Jack&#39;s New Book', '2'))
        self.now = grid()
        self.names = authors(('2', 'A. Writer'))
        self.recorded = []
        for name, value in (('ROOT', self.tmp.name), ('DATA', self.books), ('fetch', self.answer),
                            ('record', lambda *a: self.recorded.append(a))):
            patcher = mock.patch.object(sg, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def answer(self, url):
        if 'custom_widget' in url:
            return self.names
        return self.read if 'shelf=read' in url else self.now

    def run_sync(self):
        with mock.patch.dict(os.environ, {'GOODREADS_USER_ID': '1'}):
            sg.main()
        return json.load(open(self.books))['books']

    def test_titles_come_back_unescaped_with_their_review(self):
        self.assertEqual(sg.parse_grid(self.read), [('1', 'Atomic Habits: An Easy & Proven Way'), ('2', "Jack's New Book")])

    def test_a_new_finish_is_added_once_with_its_author_and_today(self):
        books = self.run_sync()
        self.assertEqual(len(books), 2)
        self.assertEqual((books[1]['title'], books[1]['author'], books[1]['source']), ("Jack's New Book", 'A. Writer', 'goodreads'))
        self.assertTrue(books[1]['finished'])
        self.assertEqual(self.recorded[-1], ('goodreads', True))
        self.assertEqual(len(self.run_sync()), 2)

    def test_a_listed_book_keeps_its_own_date(self):
        self.assertEqual(self.run_sync()[0]['finished'], '2024-01-01')

    def test_a_finish_promotes_what_was_reading(self):
        json.dump({'books': [{'title': 'Atomic Habits', 'author': '', 'status': 'reading', 'finished': ''}]}, open(self.books, 'w'))
        book = self.run_sync()[0]
        self.assertEqual(book['status'], 'read')
        self.assertTrue(book['finished'])

    def test_a_broken_answer_changes_nothing_and_says_so(self):
        for broken in ('<html>Sign in</html>', grid()):
            self.read = broken
            self.recorded.clear()
            self.assertEqual(len(self.run_sync()), 1)
            self.assertEqual(self.recorded[-1][:2], ('goodreads', False))

    def test_a_broken_answer_cannot_clear_reading_now(self):
        json.dump({'books': [{'title': 'Dune', 'author': '', 'status': 'reading', 'finished': ''}]}, open(self.books, 'w'))
        self.now = '<html>Sign in</html>'
        self.assertEqual(self.run_sync()[0]['title'], 'Dune')


if __name__ == '__main__':
    unittest.main()
