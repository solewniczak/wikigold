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

    def parse(self, wikitext):
        handler = Handler()
        for label, match in self.rlexer.tokenize(wikitext):
            handler.call(label, match)

        return {'lines': handler.lines, 'links': handler.links}