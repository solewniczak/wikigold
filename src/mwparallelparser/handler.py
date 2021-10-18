import re

from .tag import Tag
from .exceptions import TagPopException


class Handler:
    def __init__(self):
        self._tag_stack = []
        self._previous_call = None
        self._current_call = None
        self._preformatted_mode = False

        self.links = []
        self.lines = ['']  # start with first empty line

        self._titledlink_counter = 1

    def call(self, label, match):
        method = '_' + label.lower()
        self._previous_call = self._current_call
        self._current_call = method
        try:
            getattr(self, method)(match)
        except TagPopException:
            self.call('UNKNOWN', match)  # add closing tag to document if not opening tag is present
        except AttributeError:
            pass  # when we have no handler just skip the token

    def _tag_push(self, name, match):
        self._tag_stack.append(Tag(name, match))

    def _tag_pop(self, expect):
        if len(self._tag_stack) == 0:
            raise TagPopException('cannot pop empty stack')
        tag = self._tag_stack.pop()
        if tag.name != expect:
            raise TagPopException(f'expected: {expect} got: {tag.name}')

        return tag

    def _break_line(self):
        # remove end whitespaces form current line
        self.lines.append('')

    def _append_to_line(self, content):
        if len(content) == 0:  # if empty content do noting
            return
        normalized_content = ' '.join(content.split())
        if normalized_content == '':  # content was only white spaces
            self.lines[-1] += ' '
        else:
            if self.lines[-1] != '':  # append space to the the line if not the first charter in the line
                if content[0] == ' ':
                    self.lines[-1] += ' '

            self.lines[-1] += normalized_content
            if content[-1] == ' ':  # add space if was present
                self.lines[-1] += ' '

    def _append_content(self, content):
        """Additional support for glue paragraphs."""

        if len(self._tag_stack) >= 1:
            self._tag_stack[-1].append_content(content)
            return

        lines = content.split('\n')

        self._append_to_line(lines.pop(0)) # append to current line
        for line in lines:
            self.lines[-1] = self.lines[-1]
            # create new paragraph if line is empty
            if line == '' and self.lines[-1] != '':
                self._break_line()
            else:
                if self.lines[-1] != '' and self.lines[-1][-1] != ' ':
                    self.lines[-1] += ' '  # glue paragraph
                self._append_to_line(line)

    def _unknown(self, match):
        # support for Blend link https://en.wikipedia.org/wiki/Help:Wikitext#Links_and_URLs
        # check if we have some lowercase letters at the end of a link
        if self._previous_call == '_wikilink_blend':
            blend_match = re.match(r'[^\W0-9_]+', match)  # match only UNICODE alpha charters
            if blend_match:
                blend = blend_match[0]
                self.links[-1]['length'] += len(blend)

        self._append_content(match)

    def _nbsp(self, match):
        # convert &nbsp; to normal space
        self._append_content(' ')

    def _wikilink(self, match):
        self._tag_push('wikilink', match)

    def _wikilink_end(self, match):
        tag = self._tag_pop('wikilink')

        # links cannot have multilines
        if '\n' in tag.content:
            self._append_content(tag.match + tag.content + match)
            return

        link = tag.content.split('|', 1)
        if len(link) == 1 or link[1] == '':
            destination = text = link[0].strip()
        else:
            destination, text = link[0].strip(), link[1].strip()

        # ignore named namespaces like "File:", "Plik:" etc.
        if re.match('[a-z]+:', destination, re.IGNORECASE):
            return

        link = {
            'line': len(self.lines) - 1,
            'start': len(self.lines[-1]),
            'length': len(text),
            'destination': destination
        }

        # add links only when we are in top content
        if len(self._tag_stack) == 0:
            self.links.append(link)
            self._current_call = '_wikilink_blend'  # support blended links in top level
        self._append_content(text)

    def _genericlink(self, match):
        self._append_content(match)

    def _titledlink(self, match):
        match = match[1:-1]  # remove [] charters
        split = match.split(None, 1)
        if len(split) == 2:
            url, content = split
        else:
            url = match
            content = f'[{self._titledlink_counter}]'
            self._titledlink_counter += 1

        self._append_content(content)

    def _header(self, match):
        # header can only start on a line without any other content
        if re.match(r'^[ \t]*$', self.lines[-1]):
            self._tag_push('header', match)
        else:
            self._append_content(match)

    def _header_end(self, match):
        tag = self._tag_pop('header')
        header_content = tag.content.strip()
        self._append_content(header_content)
        self._break_line()  # break line after header

    def _ref(self, match):
        # check if it is an empty ref tag
        if match[-2:] != '/>':
            self._tag_push('ref', match)

    def _ref_end(self, match):
        self._tag_pop('ref')

    def _list(self, match):
        # list can only start on a line without any other content
        if not re.match(r'^[ \t]*$', self.lines[-1]):
            self._append_content(match)

    def _doublebraces(self, match):
        self._tag_push('doublebraces', match)

    def _doublebraces_end(self, match):
        self._tag_pop('doublebraces')

    def _table(self, match):
        self._tag_push('table', match)

    def _table_end(self, match):
        self._tag_pop('table')

    def _comment(self, match):
        self._tag_push('comment', match)

    def _comment_end(self, match):
        self._tag_pop('comment')

    def _div(self, match):
        self._tag_push('div', match)

    def _div_end(self, match):
        self._tag_pop('div')

    def _gallery(self, match):
        self._tag_push('gallery', match)

    def _gallery_end(self, match):
        self._tag_pop('gallery')

    def _score(self, match):
        self._tag_push('score', match)

    def _score_end(self, match):
        self._tag_pop('score')
