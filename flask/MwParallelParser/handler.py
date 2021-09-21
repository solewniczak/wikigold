import re

from MwParallelParser.tag import Tag, TagPopException


class Handler:
    def __init__(self):
        self._tag_stack = []
        self._skip_content_tags = ['doublebraces', 'table', 'comment', 'div', 'gallery']
        self.links = []
        self.lines = [''] # start with first empty line

    def __getattr__(self, method_name):
        def method(*args, **kwargs):
            tag_name = method_name.split('_', 1)[0]
            if tag_name not in self._skip_content_tags:
                raise AttributeError(f'No handler for {method_name}')

            if method_name[-4:] == '_end':
                self._tag_pop(tag_name)
            else:
                self._tag_push(tag_name)
        return method

    def call(self, label, match):
        method = label.lower()
        try:
            getattr(self, method)(match)
        except TagPopException:
            self.call('UNKNOWN', match)  # add closing tag to document if not opening tag is present

    def _tag_push(self, name):
        self._tag_stack.append(Tag(name))

    def _tag_pop(self, expect):
        if len(self._tag_stack) == 0:
            raise TagPopException('cannot pop empty stack')
        tag = self._tag_stack.pop()
        if tag.name != expect:
            raise TagPopException(f'expected: {expect} got: {tag.name}')

        return tag

    def _append_content(self, content):
        if len(self._tag_stack) >= 1:
            self._tag_stack[-1].append_content(content)
            return

        lines = content.split('\n')

        self.lines[-1] += lines.pop() # append to current line
        for line in lines:
            self.lines.append(line)

    def unknown(self, match):
        self._append_content(match)

    def wikilink(self, match):
        self._tag_push('wikilink')

    def wikilink_end(self, match):
        tag = self._tag_pop('wikilink')

        link = tag.content.split('|', 1)
        if len(link) == 1 or link[1] == '':
            destination = text = link[0]
        else:
            destination, text = link[0].strip(), link[1].strip()

        # ignore named namespaces like "File:", "Plik:" etc.
        if re.match('[a-z]+:', destination, re.IGNORECASE):
            return

        link = {
            'line': len(self.lines)-1,
            'start': len(self.lines[-1]),
            'length': len(text),
            'destination': destination
        }

        # add links only when we are in top content
        if len(self._tag_stack) == 0:
            self.links.append(link)
        self._append_content(text)