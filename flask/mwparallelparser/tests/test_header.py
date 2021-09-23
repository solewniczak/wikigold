import unittest

from mwparallelparser import Parser


class HeaderTestCase(unittest.TestCase):

    def test_basic(self):
        parser = Parser()
        wikitext = '== Header ==\nContent'
        result = parser.parse(wikitext)
        self.assertEqual(result['lines'], ['Header', 'Content'])