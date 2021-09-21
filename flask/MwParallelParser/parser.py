from MwParallelParser.handler import Handler
from MwParallelParser.rlexer import Rlexer


class Parser:
    def __init__(self):
        self.name = 'MwParallelParser'
        self.version = '1.0.0'

        self.rlexer = Rlexer()
        self.handler = Handler()

        # load token patterns
        tokens = {}
        filename = 'tokens'
        with open(filename) as file:
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

        filename = 'mode_bind'
        with open(filename) as file:
            for line in file:
                line_split = line.split()
                mode, bind_list = line_split[0], line_split[1:]
                for bind in bind_list:
                    if bind in tokens:
                        token = tokens[bind]
                        self.rlexer.add_rule(mode, token[0], bind, token[1])

        self.rlexer.build()

    def parse(self, wikitext):
        for label, match in self.rlexer.tokenize(wikitext):
            self.handler.call(label, match)

        return {'lines': self.handler.lines, 'links': self.handler.links}