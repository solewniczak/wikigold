from MwParallelParser.parser import Parser

wikitext = '''This is [[test]]ekstra.
[https://rid.pl] [https://gnu.org] https://rid.pl
[[Help]]<nowiki />ful advice'''

parser = Parser()

d = parser.parse(wikitext)
print(d)