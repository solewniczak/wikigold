from mwparallelparser.tests.parsertestcase import ParserTestCase


class ListTestCase(ParserTestCase):
    def test_basic(self):
        wikitext = '* List Element'
        self.assertParsed(wikitext, ['List Element'])
