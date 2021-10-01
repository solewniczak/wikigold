from mwparallelparser.tests.parsertestcase import ParserTestCase

class HeaderTestCase(ParserTestCase):

    def test_basic(self):
        wikitext = '== Header ==\nContent'
        self.assertParsed(wikitext, ['Header', 'Content'])
