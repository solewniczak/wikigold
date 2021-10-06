from mwparallelparser.tests.parsertestcase import ParserTestCase

class HeaderTestCase(ParserTestCase):

    def test_basic(self):
        wikitext = '== Header ==\nContent'
        self.assertParsed(wikitext, ['Header', 'Content'])

    def test_header_not_on_the_begining(self):
        wikitext = 'Content1\n== Header ==\nContent2'
        self.assertParsed(wikitext, ['Content1', 'Header', 'Content2'])
