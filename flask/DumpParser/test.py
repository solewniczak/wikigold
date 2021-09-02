import re

import mwparserfromhell

text = '''[[File:Unix timeline.en.svg|thumb|right|The history of UNIX and its variants]]

''UNIX'' is a computer [[operating system]]. It was first developed in [[1969]] at [[Bell Labs]].'''
code = mwparserfromhell.parse(text)

for wikilink in code.filter_wikilinks():
    title = wikilink.title.strip_code().strip()
    if title.startswith('File:'):
        code.remove(wikilink)

re_special_link = re.compile(r'\[\[(File|Image):.*?\]\]')
print(code.strip_code())

print()
code = code.strip_code()
code = re_special_link.sub('', code)
print(code)