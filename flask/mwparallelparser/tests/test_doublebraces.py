import unittest

from mwparallelparser import Parser


class DoublebracesTestCase(unittest.TestCase):

    def test_basic(self):
        parser = Parser()
        wikitext = '{{This will be deleted}}'
        result = parser.parse(wikitext)
        self.assertEqual(result['lines'], [''])

    def test_embeded(self):
        parser = Parser()
        wikitext = '{{This <ref>{{This is a test}}</ref>}}'
        result = parser.parse(wikitext)
        self.assertEqual(result['lines'], [''])

    def test_with_ref_and_link_after(self):
        parser = Parser()
        wikitext = 'to<ref>{{Cytuj stronę |url=http://www.mytopdozen.com/Best_Polish_Composers.html |tytuł=Lista polskich kompozytorów najczęściej wymienianych w internecie |język=en |data dostępu=3 grudnia 2008}}</ref>: [[Fryderyk Chopin]]'
        result = parser.parse(wikitext)
        self.assertEqual(result['lines'], ['to: Fryderyk Chopin'])

