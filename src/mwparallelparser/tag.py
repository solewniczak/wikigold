class Tag:
    def __init__(self, name, match):
        self.name = name
        self.match = match
        self.content = ''

    def append_content(self, content):
        self.content += content
