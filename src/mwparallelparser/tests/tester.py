import os

from mwparallelparser import Parser

filepath = os.path.join(os.path.dirname(__file__), 'wikicode')
with open(filepath) as file:
    wikitext = file.read()
parser = Parser()
result = parser.parse(wikitext)
print(result['lines'])
