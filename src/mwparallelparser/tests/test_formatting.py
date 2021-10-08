from mwparallelparser.tests.parsertestcase import ParserTestCase


class FormattingTestCase(ParserTestCase):
    def test_italic(self):
        wikitext = "''Test''"
        self.assertParsed(wikitext, ['Test'])
