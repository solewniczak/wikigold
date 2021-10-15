import unittest

from mwparallelparser.tests.parsertestcase import ParserTestCase


class ParagraphTestCase(ParserTestCase):
    def test_basic(self):
        wikitext = 'This is a paragraph\n\nThis is next'
        self.assertParsed(wikitext, ['This is a paragraph', 'This is next'])

    def test_ident_text(self):
        wikitext = 'This is a paragraph\n:This is next'
        self.assertParsed(wikitext, ['This is a paragraph', 'This is next'])

    def test_bullet_list(self):
        wikitext = 'This is a paragraph\n* This is next\n** And That'
        self.assertParsed(wikitext, ['This is a paragraph', 'This is next', 'And That'])

    def test_numbered_list(self):
        wikitext = 'This is a paragraph\n# This is next\n## And That'
        self.assertParsed(wikitext, ['This is a paragraph', 'This is next', 'And That'])

    def test_definition_list(self):
        wikitext = 'This is a paragraph\n; This is next\n: And That'
        self.assertParsed(wikitext, ['This is a paragraph', 'This is next', 'And That'])

    def test_glue_to_paragraph(self):
        wikitext = 'This is a paragraph\nthis is continuation'
        self.assertParsed(wikitext, ['This is a paragraph this is continuation'])

    def test_extra_newlines(self):
        wikitext = 'This is a paragraph\n\n{{some template}}\n\nThis is next'
        self.assertParsed(wikitext, ['This is a paragraph', 'This is next'])

    def test_extra_spaces_between_words(self):
        wikitext = 'This     is     a paragraph'
        self.assertParsed(wikitext, ['This is a paragraph'])

    @unittest.skip
    def test_preformatted_paragraph(self):
        wikitext = '  This     is     a paragraph'
        self.assertParsed(wikitext, ['This     is     a paragraph'])

    @unittest.skip
    def test_preformatted_paragraph_with_markup(self):
        wikitext = "  This     is     a '''paragraph'''"
        self.assertParsed(wikitext, ['This     is     a paragraph'])

    @unittest.skip
    def test_preformatted_multi_paragraph(self):
        wikitext = ' This     is     a paragraph\n  There are two spaces!'
        self.assertParsed(wikitext, ['This     is     a paragraph', ' There are two spaces!'])

    @unittest.skip
    def test_preformatted_and_standard_paragraph_after(self):
        wikitext = ' This     is     a paragraph\nThis    is   standard'
        self.assertParsed(wikitext, ['This     is     a paragraph', 'This is standard'])