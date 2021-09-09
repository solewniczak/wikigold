class Parser:
    def __init__(self):
        self.name = 'MwParallelParser'
        self.version = '1.0.0'

    def parse(self, wikitext):
        return {'lines': wikitext.split('\n'), 'links': []}