from mwparallelparser.tests.parsertestcase import ParserTestCase


class WikilinkTestCase(ParserTestCase):
    def test_link(self):
        wikitext = '[[hipertekst]] something'
        links = [{'line': 0, 'start': 0, 'length': 10, 'destination': 'hipertekst'}]
        self.assertParsed(wikitext, ['hipertekst something'], links)

    def test_files_removal(self):
        wikitext = "[[Plik:Jan Matejko, Stańczyk.jpg|mały|lewo|[[Jan Matejko]], ''[[Stańczyk (obraz Jana Matejki)|Stańczyk]]'']]"
        self.assertParsed(wikitext, [])

    def test_blend_link(self):
        wikitext = '[[klasycyzm]]em'
        links = [{'line': 0, 'start': 0, 'length': 11, 'destination': 'klasycyzm'}]
        self.assertParsed(wikitext, ['klasycyzmem'], links)

    def test_blend_link_in_quotes(self):
        wikitext = '"[[hipertekst]]" something'
        links = [{'line': 0, 'start': 1, 'length': 10, 'destination': 'hipertekst'}]
        self.assertParsed(wikitext, ['"hipertekst" something'], links)

    def test_blend_link_in_round_brackets(self):
        wikitext = '([[1971]]) something'
        links = [{'line': 0, 'start': 1, 'length': 4, 'destination': '1971'}]
        self.assertParsed(wikitext, ['(1971) something'], links)

    def test_blend_link_with_polish_chars(self):
        wikitext = '[[ąę]]żźćółąę something'
        links = [{'line': 0, 'start': 0, 'length': 9, 'destination': 'ąę'}]
        self.assertParsed(wikitext, ['ąężźćółąę something'], links)

    def test_titled_link(self):
        wikitext = '[http://example.com I am a link].'
        self.assertParsed(wikitext, ['I am a link.'])

    def test_titled_link_with_utf8(self):
        wikitext = '[http://example.com Żółć].'
        self.assertParsed(wikitext, ['Żółć.'])

    def test_titled_link_without_ending_bracket(self):
        wikitext = 'some <ref>[http://example.com It should work by now</ref>content [[and link]].'
        self.assertParsed(wikitext, ['some content and link.'])
