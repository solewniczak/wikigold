import re

import mwparserfromhell
import logging
from bs4 import BeautifulSoup


class MWParserFromHellLinks:
    '''No word-ending links. All titles with ":" are removed.'''

    def __init__(self, wikitext, titles_in_ns0):
        self._wikicode = mwparserfromhell.parse(wikitext)
        self._titles_in_ns0 = titles_in_ns0
        self._special_namespaces = ['File', 'Image']
        self._re_special_link = re.compile(r'\[\[(File|Image):.*?\]\]')

    def get_wikicode(self):
        return self._wikicode

    def get_lines(self):
        for wikilink in self._wikicode.filter_wikilinks():
            title = wikilink.title.strip_code().strip()
            if title.startswith('File:') or title.startswith('Image:'):
                try:
                    self._wikicode.remove(wikilink)
                except ValueError:
                    print(f'cannot remove: {title}. not found')

        strip_code = self._wikicode.strip_code()
        strip_code = self._re_special_link.sub('', strip_code)
        lines = strip_code.strip().split('\n') # remove empty chars from the begin and end
        lines = list(map(lambda line: line.strip(), lines))  # remove whitespaces
        lines = list(map(lambda line: ' '.join(line.split()), lines))  # normalize whitespaces

        lines_normalized = [lines[0]]
        for i in range(1, len(lines)):
            if lines[i] != '' or (lines[i] == '' and lines[i-1] != ''):
                lines_normalized.append(lines[i])

        return lines_normalized

    def get_links(self):
        links = []
        for wikilink in self._wikicode.filter_wikilinks():
            title = wikilink.title.strip_code().strip()
            if len(title) == 0:
                logging.info(f"Ignoring empty title: {wikilink.title}")
                continue

            # check if title goes to existing page
            title_underscored = title.replace(' ', '_')
            if len(title_underscored) > 1:
                title_underscored = title_underscored[0].upper() + title_underscored[1:]
            else:
                title_underscored = title_underscored[0].upper()
            if title_underscored not in self._titles_in_ns0:
                logging.info(f"Not in titles_in_ns0: {title} IGNORING")
                continue

            if wikilink.text is None:
                text = title
            else:
                text = wikilink.text.strip_code().strip()

                # check if text still contains some unnecessery tags
                if text.find('<') != -1:
                    new_text = BeautifulSoup(text).text
                    logging.info(f"BeautifulSoup from {text} to {new_text}")
                    text = new_text
                # remove some artifacts
                new_text = text.replace("'''", "")
                new_text = new_text.replace("''", "")
                if text != new_text:
                    logging.info(f"Artifacts removal from {text} to {new_text}")
                text = new_text

            links.append({'text': text, 'title': title_underscored})

        return links
