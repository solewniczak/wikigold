from MwParallelParser.parser import Parser

wikitext = '''{{template}}
Pierwszy [[test]]!'''

parser = Parser()

d = parser.parse(wikitext)
print(d)