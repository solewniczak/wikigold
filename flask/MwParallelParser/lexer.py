class Lexer:

    def __init__(self):
        self.patterns = []
        self.compounded = None

    def add(self, regex, label):
        self.patterns.append((regex, label))

    def build(self):
        """
        Create compounded regex. Ready to consume.
        :return:
        """
        regexes = []
        for regex, label in self.patterns:
            regexes.append('(' + regex + ')')
        self.compounded = '|'.join(regexes)

    def consume(self, doc):
        self.tokens = []
        self.doc = doc

    def advance(self):
        pass