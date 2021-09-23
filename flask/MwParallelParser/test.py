from MwParallelParser.parser import Parser

wikitext = '''This is [[test]]ekstra.'''

parser = Parser()

d = parser.parse(wikitext)
print(d)