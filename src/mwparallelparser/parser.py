import os

from .rlexer import Rlexer
from .handler import Handler


class Parser:
    def __init__(self):
        self.name = 'MwParallelParser'
        self.version = '1.0.0'

        self.rlexer = Rlexer()

        # load token patterns
        tokens = {}
        filepath = os.path.join(os.path.dirname(__file__), 'tokens')
        with open(filepath) as file:
            for line in file:
                line = line.rstrip()
                label, pattern = line.split(None, 1)
                if '>' in label:
                    label, next_state = label.split('>')
                    tokens[label] = (pattern, ('push', next_state))
                elif label[-1] == '<':
                    label = label[:-1]
                    tokens[label] = (pattern, ('pop', ))
                else:
                    tokens[label] = (pattern, None)

        filepath = os.path.join(os.path.dirname(__file__), 'mode_bind')
        with open(filepath) as file:
            for line in file:
                line_split = line.split()
                mode, bind_list = line_split[0], line_split[1:]
                for bind in bind_list:
                    if bind in tokens:
                        token = tokens[bind]
                        self.rlexer.add_rule(mode, token[0], bind, token[1])

        self.rlexer.build()

    @classmethod
    def trim(cls, lines, links):
        start = 0
        while start < len(lines) and lines[start] == '':
            start += 1
        end = len(lines)
        while end > 0 and lines[end-1] == '':
            end -= 1

        # update link lines
        for link in links:
            link['line'] -= start

        return lines[start:end], links

    def parse(self, wikitext, trim=True):
        handler = Handler()
        for label, match in self.rlexer.tokenize(wikitext):
            handler.call(label, match)

        lines, links = handler.lines, handler.links
        if trim:
            lines, links = self.trim(lines, links)

        return {'lines': lines, 'links': links}