import re


class Lexer:

    def __init__(self):
        self.patterns = []
        self.labels = []
        self.tokens = []
        self.doc = ''
        self.flags = re.IGNORECASE | re.MULTILINE | re.DOTALL
        self.compounded_pattern = None

    def add_rule(self, pattern, label):
        if self.compounded_pattern:
            raise Exception('cannot add patterns after the build.')
        self.patterns.append(pattern)
        self.labels.append(label)

    def build(self):
        """
        Create compounded regex. Ready to consume.
        :return:
        """
        regexes = []
        for regex in self.patterns:
            regexes.append('(' + regex + ')')
        compounded_pattern = '|'.join(regexes)
        self.compounded_pattern = re.compile(compounded_pattern, self.flags)

    def consume(self, doc):
        if self.compounded_pattern is None:
            raise Exception('build the Lexer first.')

        self.tokens = []
        self.doc = doc

    def advance(self):
        """
        Get next token from the document.

        :return: Tuple: (label, match, post)
        """
        if len(self.tokens) == 0:
            if self.doc == '':
                return None

            pre, label, match = self.split()
            if pre != '':
                self.tokens.append(('UNKNOWN', pre))
            if match != '':
                self.tokens.append((label, match))

        label, match = self.tokens.pop(0)
        self.doc = self.doc[len(match):]  # remove token from document
        return label, match, self.doc

    def split(self):
        match = self.compounded_pattern.search(self.doc)
        if not match:
            return self.doc, '', ''

        idx = match.lastindex
        label = self.labels[idx-1]  # first element is entire string
        pre = self.doc[:match.start(idx)]
        match = self.doc[match.start(idx):match.end(idx)]
        # post = self.doc[match.end(idx):]
        return pre, label, match

    def tokenize(self, doc):
        self.consume(doc)
        while True:
            advance = self.advance()
            if advance is None:
                break
            yield advance
