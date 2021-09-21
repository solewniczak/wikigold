class TagPopException(Exception):
    pass


class Tag:
    def __init__(self, name):
        self.name = name
        self.content = ''

    def append_content(self, content):
        self.content += content
