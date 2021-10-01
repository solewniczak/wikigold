import unittest

from mwparallelparser import Parser


class ParserTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def assertParsed(self, wikitext, lines, links=None):
        result = self.parser.parse(wikitext)
        self.assertEqual(result['lines'], lines)
        if links is not None:
            self.assertEqual(result['links'], links)