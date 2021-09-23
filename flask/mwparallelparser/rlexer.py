from collections import defaultdict

from .lexer import Lexer


class Rlexer:
    def __init__(self):
        self.lexers = {'base': Lexer()}
        self.transitions = defaultdict(dict)

        self.state_stack = ['base']
        self.doc = ''

    def add_rule(self, state, pattern, label, next_state=None):
        # next_state: None - stay in current state; ('push', 'state') - push to new state; ('pop', 1)- pop state
        if state not in self.lexers:
            self.lexers[state] = Lexer()

        self.lexers[state].add_rule(pattern, label)
        if next_state:
            self.transitions[state][label] = next_state

    def build(self):
        # prepare lexers
        for _, lexer in self.lexers.items():
            lexer.build()

    def consume(self, doc):
        self.state_stack = ['base']
        self.doc = doc
        self.lexers['base'].consume(self.doc)

    def advance(self):
        """
        Get next token from the document.

        :return: Tuple: (label, match)
        """
        state = self.state_stack[-1]
        advance = self.lexers[state].advance()
        if advance is None:
            return None

        label, match, self.doc = advance

        if label in self.transitions[state]:
            transition = self.transitions[state][label]
            if transition[0] == 'push':
                self.state_stack.append(transition[1])
            elif transition[0] == 'pop':
                self.state_stack.pop()

            next_state = self.state_stack[-1]
            self.lexers[next_state].consume(self.doc)

        return label, match

    def tokenize(self, doc):
        self.consume(doc)
        while True:
            advance = self.advance()
            if advance is None:
                break
            yield advance