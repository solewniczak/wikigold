from MwParallelParser.parser import Parser

wikitext = 'Pierwszy [[test]]!'

parser = Parser()

parser.parse(wikitext)