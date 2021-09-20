from collections import defaultdict

from MwParallelParser.lexer import Lexer


class Rlexer:
    def __init__(self):
        self.lexers = {'base': Lexer()}
        self.transitions = defaultdict(dict)
        self.states = ['base']

    def add(self, state, pattern, label, next=None):
        """
        :param state:
        :param pattern:
        :param label:
        :param next: None - stay in current state; ">something" - push to new state; "<" - pop state
        :return:
        """
        if state not in self.lexers:
            self.lexers[state] = Lexer()

        self.lexers[state].push(pattern, label)
        if next is not None:
            if next[0] == '>':
                self.transitions[state][label] = ('push', next[1:])
            elif next == '<':
                self.transitions[state][label] = ('pop', )
            else:
                raise Exception('next should be ">state" or "<"')

    def consume(self, doc):
        """
        Load document into Lexer.
        :param data:
        :return:
        """
        self.doc = doc
        self.lexers['base'].consume(self.doc)

    def advance(self):
        """
        Get next token from the document.

        :return: Tuple|None: (token, match)
        """
        state = self.states[-1]
        advance = self.lexers[state].advance(self.doc)
        if advance is None:
            return None

        label = advance[0]
        if label in self.transitions[state]:
            transition = self.transitions[state][label]
            if transition[0] == 'push':
                self.states.append(transition[1])
            elif transition[0] == 'pop':
                if len(self.states) == 1:
                    raise Exception('cannot pop "base" state.')
                self.states.pop()

            next_state = self.states[-1]
            self.lexers[next_state].consume(self.doc)

        return advance